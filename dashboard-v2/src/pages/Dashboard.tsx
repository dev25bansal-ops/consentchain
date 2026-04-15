import React, { useEffect, useState, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import { useWallet } from "../hooks/useWallet";
import api from "../lib/api";
import { format } from "date-fns";
import {
  RefreshCw,
  Plus,
  ExternalLink,
  Ban,
  RotateCcw,
  Search,
  Filter,
  LayoutList,
  LayoutGrid,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { staggerContainer, staggerItem, fadeInUp } from "../lib/animations";
import CreateConsentModal from "../components/CreateConsentModal";

interface Consent {
  consent_id: string;
  fiduciary_id: string;
  purpose: string;
  data_types: string[];
  status: string;
  granted_at: string;
  expires_at: string;
  consent_hash: string;
}

interface Stats {
  total: number;
  active: number;
  revoked: number;
  expired: number;
}

export default function Dashboard() {
  const { address } = useWallet();
  const [stats, setStats] = useState<Stats>({
    total: 0,
    active: 0,
    revoked: 0,
    expired: 0,
  });
  const [consents, setConsents] = useState<Consent[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");
  const [filtersOpen, setFiltersOpen] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, [address, filter]);

  // Debounced search effect
  const debouncedSearch = useCallback((value: string) => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    searchTimeoutRef.current = setTimeout(() => {
      loadDashboardData(value);
    }, 300);
  }, []);

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    debouncedSearch(value);
  };

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, []);

  async function loadDashboardData(searchTerm?: string) {
    try {
      const params: Record<string, string | number> = { limit: 50 };
      if (searchTerm) params.search = searchTerm;
      if (filter !== "all") params.status = filter;

      const response = await api.get("/api/v1/consent/query", { params });
      const consentsData = response.data?.data?.consents || [];
      setConsents(consentsData);

      setStats({
        total: consentsData.length,
        active: consentsData.filter((c: Consent) => c.status === "GRANTED")
          .length,
        revoked: consentsData.filter((c: Consent) => c.status === "REVOKED")
          .length,
        expired: consentsData.filter((c: Consent) => c.status === "EXPIRED")
          .length,
      });
    } catch (error) {
      console.error("Failed to load dashboard data:", error);
    } finally {
      setLoading(false);
    }
  }

  async function handleRefresh() {
    setRefreshing(true);
    await loadDashboardData(searchQuery);
    setTimeout(() => setRefreshing(false), 600);
  }

  async function revokeConsent(consentId: string) {
    try {
      await api.post("/api/v1/consent/revoke", {
        consent_id: consentId,
        reason: "User requested revocation",
        signature: "pending_wallet_signature",
      });
      loadDashboardData();
    } catch (error) {
      console.error("Failed to revoke consent:", error);
    }
  }

  // Server-side filtering is now applied via API params
  const displayConsents = consents;

  const filterChips = [
    { label: "All", value: "all", count: stats.total },
    { label: "Active", value: "active", count: stats.active },
    { label: "Revoked", value: "revoked", count: stats.revoked },
    { label: "Expired", value: "expired", count: stats.expired },
    { label: "Pending", value: "pending", count: 0 },
    { label: "Last 30 days", value: "last30", count: 0 },
    { label: "Financial", value: "financial", count: 0 },
    { label: "Healthcare", value: "healthcare", count: 0 },
  ];

  return (
    <div>
      <motion.div
        variants={fadeInUp}
        initial="initial"
        animate="animate"
        style={styles.pageHdr}
      >
        <div>
          <h1 style={styles.pageTitle}>My Consents</h1>
          <p style={styles.pageSub}>
            Manage and monitor your on-chain data consent records
          </p>
        </div>
        <div style={styles.hdrActions}>
          <motion.button
            onClick={handleRefresh}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            style={styles.btnSecondary}
          >
            <RefreshCw
              size={14}
              style={{ animation: refreshing ? "spin 0.6s linear" : "none" }}
            />
            Refresh
          </motion.button>
          <motion.button
            onClick={() => setShowCreateModal(true)}
            whileHover={{ scale: 1.02, y: -1 }}
            whileTap={{ scale: 0.98 }}
            style={styles.btnPrimary}
          >
            <Plus size={14} />
            New Consent
          </motion.button>
        </div>
      </motion.div>

      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        style={styles.statsGrid}
      >
        <StatCard
          label="Total"
          value={stats.total}
          type="total"
          trend="All consent records"
          delay={0.05}
        />
        <StatCard
          label="Active"
          value={stats.active}
          type="active"
          trend="Currently valid"
          delay={0.1}
        />
        <StatCard
          label="Revoked"
          value={stats.revoked}
          type="revoked"
          trend="Withdrawn by you"
          delay={0.15}
        />
        <StatCard
          label="Expired"
          value={stats.expired}
          type="expired"
          trend="Past validity period"
          delay={0.2}
        />
      </motion.div>

      <motion.div
        variants={fadeInUp}
        initial="initial"
        animate="animate"
        transition={{ delay: 0.1 }}
        style={styles.toolbar}
      >
        <div style={styles.searchBar}>
          <Search size={15} color="#5a5480" />
          <input
            type="text"
            placeholder="Search by consent hash or purpose..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            style={styles.searchInput}
          />
        </div>
        <motion.button
          onClick={() => setFiltersOpen(!filtersOpen)}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          style={{
            ...styles.filterBtn,
            ...(filtersOpen ? styles.filterBtnActive : {}),
          }}
        >
          <Filter size={14} />
          Filters
        </motion.button>
        <div style={styles.viewToggle}>
          <motion.div
            onClick={() => setViewMode("list")}
            whileHover={{ scale: 1.05 }}
            style={{
              ...styles.viewBtn,
              ...(viewMode === "list" ? styles.viewBtnActive : {}),
            }}
          >
            <LayoutList size={15} />
          </motion.div>
          <motion.div
            onClick={() => setViewMode("grid")}
            whileHover={{ scale: 1.05 }}
            style={{
              ...styles.viewBtn,
              ...(viewMode === "grid" ? styles.viewBtnActive : {}),
            }}
          >
            <LayoutGrid size={15} />
          </motion.div>
        </div>
      </motion.div>

      {filtersOpen && (
        <motion.div
          variants={fadeInUp}
          initial="initial"
          animate="animate"
          transition={{ delay: 0.15 }}
          style={styles.filterChips}
        >
          {filterChips.map((chip) => (
            <motion.div
              key={chip.value}
              onClick={() => setFilter(chip.value)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              style={{
                ...styles.chip,
                ...(filter === chip.value ? styles.chipActive : {}),
              }}
            >
              {chip.label} {chip.value === "all" && `(${chip.count})`}
            </motion.div>
          ))}
        </motion.div>
      )}

      {loading ? (
        <div style={styles.loadingContainer}>
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            style={styles.spinner}
          />
        </div>
      ) : displayConsents.length === 0 ? (
        <motion.div
          variants={fadeInUp}
          initial="initial"
          animate="animate"
          style={styles.emptyState}
        >
          <motion.div
            animate={{ y: [0, -8, 0] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            style={styles.emptyIcon}
          >
            <svg viewBox="0 0 36 36" fill="none" width={36} height={36}>
              <path
                d="M18 4L28 9V18C28 24 23.5 29.5 18 31C12.5 29.5 8 24 8 18V9L18 4Z"
                stroke="currentColor"
                strokeWidth="1.5"
              />
              <path
                d="M13 18L16.5 21.5L23 15"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </motion.div>
          <div style={styles.emptyTitle}>No consents found</div>
          <div style={styles.emptySub}>
            Get started by granting your first consent to a data fiduciary
            registered under DPDP Act 2023
          </div>
          <div style={styles.emptyHint}>
            <strong style={{ color: "#a78bfa" }}>How it works:</strong> Consents
            are created when you authorise a data fiduciary to process your
            personal data. Each consent is recorded as an immutable transaction
            on Algorand.
          </div>
          <motion.button
            onClick={() => setShowCreateModal(true)}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            style={{
              ...styles.btnPrimary,
              fontSize: 13,
              padding: "10px 20px",
              marginTop: 24,
            }}
          >
            <Plus size={14} />
            Grant First Consent
          </motion.button>
        </motion.div>
      ) : (
        <>
          <motion.div
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            style={styles.consentList}
          >
            {displayConsents.map((consent, index) => (
              <ConsentCard
                key={consent.consent_id}
                consent={consent}
                onRevoke={() => revokeConsent(consent.consent_id)}
                delay={index * 0.05}
              />
            ))}
          </motion.div>

          <motion.div
            variants={fadeInUp}
            initial="initial"
            animate="animate"
            transition={{ delay: 0.25 }}
            style={styles.pagination}
          >
            <div style={styles.pageInfo}>
              Showing {displayConsents.length} of {stats.total} consents
            </div>
            <div style={styles.pageBtns}>
              <motion.div
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                style={styles.pgBtn}
              >
                <ChevronLeft size={14} />
              </motion.div>
              <motion.div
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                style={{ ...styles.pgBtn, ...styles.pgBtnActive }}
              >
                1
              </motion.div>
              <motion.div
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                style={styles.pgBtn}
              >
                <ChevronRight size={14} />
              </motion.div>
            </div>
          </motion.div>
        </>
      )}

      <CreateConsentModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={loadDashboardData}
      />
    </div>
  );
}

const StatCard = React.memo(function StatCard({
  label,
  value,
  type,
  trend,
  delay,
}: {
  label: string;
  value: number;
  type: "total" | "active" | "revoked" | "expired";
  trend: string;
  delay: number;
}) {
  const [displayValue, setDisplayValue] = useState(0);
  const hasAnimated = useRef(false);

  useEffect(() => {
    if (hasAnimated.current) return;
    hasAnimated.current = true;

    const duration = 900;
    const steps = duration / 16;
    const stepValue = value / steps;
    let current = 0;

    const timer = setTimeout(() => {
      const animate = () => {
        current = Math.min(current + stepValue, value);
        setDisplayValue(Math.round(current));
        if (current < value) requestAnimationFrame(animate);
        else setDisplayValue(value);
      };
      animate();
    }, 300);

    return () => clearTimeout(timer);
  }, [value]);

  const config = {
    total: {
      color: "#3b82f6",
      gradient: "linear-gradient(90deg, #3b82f6, #6366f1)",
    },
    active: {
      color: "#10b981",
      gradient: "linear-gradient(90deg, #10b981, #34d399)",
    },
    revoked: {
      color: "#f43f5e",
      gradient: "linear-gradient(90deg, #f43f5e, #fb7185)",
    },
    expired: {
      color: "#f59e0b",
      gradient: "linear-gradient(90deg, #f59e0b, #fbbf24)",
    },
  };

  return (
    <motion.div
      variants={staggerItem}
      transition={{ delay }}
      whileHover={{ y: -2 }}
      style={{
        ...styles.statCard,
        borderTop: `2px solid ${config[type].gradient}`,
      }}
    >
      <div style={{ ...styles.statGlow, background: config[type].color }} />
      <div style={styles.statLabel}>
        <motion.div
          animate={
            type === "active"
              ? { scale: [1, 1.2, 1], opacity: [1, 0.4, 1] }
              : {}
          }
          transition={{ duration: 2, repeat: Infinity }}
          style={{
            ...styles.statDot,
            background: config[type].color,
            boxShadow:
              type === "active" ? `0 0 6px ${config[type].color}` : "none",
          }}
        />
        {label}
      </div>
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: delay + 0.1 }}
        style={{ ...styles.statNum, color: config[type].color }}
      >
        {displayValue}
      </motion.div>
      <div style={styles.statTrend}>{trend}</div>
    </motion.div>
  );
});

const ConsentCard = React.memo(function ConsentCard({
  consent,
  onRevoke,
  delay,
}: {
  consent: Consent;
  onRevoke: () => void;
  delay: number;
}) {
  const statusConfig: Record<
    string,
    {
      color: string;
      bg: string;
      border: string;
      icon: string;
      cardClass: string;
    }
  > = {
    GRANTED: {
      color: "#34d399",
      bg: "rgba(16,185,129,0.1)",
      border: "rgba(16,185,129,0.2)",
      icon: "🏦",
      cardClass: "c-active",
    },
    REVOKED: {
      color: "#fb7185",
      bg: "rgba(244,63,94,0.1)",
      border: "rgba(244,63,94,0.2)",
      icon: "🛒",
      cardClass: "c-revoked",
    },
    EXPIRED: {
      color: "#fbbf24",
      bg: "rgba(245,158,11,0.1)",
      border: "rgba(245,158,11,0.2)",
      icon: "🚗",
      cardClass: "c-expired",
    },
    PENDING: {
      color: "#60a5fa",
      bg: "rgba(59,130,246,0.1)",
      border: "rgba(59,130,246,0.2)",
      icon: "⏳",
      cardClass: "c-pending",
    },
  };

  const config = statusConfig[consent.status] || statusConfig.PENDING;
  const isActive = consent.status === "GRANTED";
  const isExpired = consent.status === "EXPIRED";
  const isRevoked = consent.status === "REVOKED";

  const timelinePercent = getTimelinePercent(
    consent.granted_at,
    consent.expires_at,
  );

  return (
    <motion.div
      variants={staggerItem}
      transition={{ delay }}
      whileHover={{ y: -1 }}
      style={{ ...styles.consentCard, borderLeftColor: config.color }}
    >
      <div
        style={{
          ...styles.consentIcon,
          background: config.bg,
          border: `1px solid ${config.border}`,
        }}
      >
        {config.icon}
      </div>

      <div style={styles.consentBody}>
        <div style={styles.consentTop}>
          <span style={styles.consentOrg}>{consent.fiduciary_id}</span>
          <span
            style={{
              ...styles.statusBadge,
              background: config.bg,
              color: config.color,
              border: `1px solid ${config.border}`,
            }}
          >
            <motion.span
              animate={
                isActive ? { scale: [1, 1.2, 1], opacity: [1, 0.4, 1] } : {}
              }
              transition={{ duration: 1.5, repeat: Infinity }}
              style={{ ...styles.statusDot, background: config.color }}
            />
            {consent.status}
          </span>
        </div>
        <div style={styles.consentPurpose}>{consent.purpose}</div>
        <div style={styles.consentTags}>
          {consent.data_types.slice(0, 3).map((type) => (
            <span key={type} style={styles.tag}>
              {type.replace(/_/g, " ")}
            </span>
          ))}
        </div>

        {(isActive || isExpired) && consent.expires_at && (
          <div style={styles.timelineBar}>
            <span style={styles.tlLabel}>{isActive ? "Valid" : "Expired"}</span>
            <div style={styles.tlTrack}>
              <div
                style={{
                  ...styles.tlFill,
                  width: `${timelinePercent}%`,
                  background: isActive
                    ? "linear-gradient(90deg, #10b981, #34d399)"
                    : "linear-gradient(90deg, #f59e0b, #fbbf24)",
                }}
              />
            </div>
            <span style={styles.tlLabel}>
              Expires{" "}
              {consent.expires_at
                ? format(new Date(consent.expires_at), "MMM yyyy")
                : "N/A"}
            </span>
          </div>
        )}
      </div>

      <div style={styles.consentMeta}>
        <div style={styles.consentHash}>
          {consent.consent_hash?.slice(0, 10)}…
        </div>
        <div style={styles.consentDate}>
          {consent.granted_at
            ? `Granted ${format(new Date(consent.granted_at), "dd MMM yyyy")}`
            : "N/A"}
        </div>
        <div style={styles.consentActions}>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            style={{
              ...styles.actBtn,
              background: "rgba(124,58,237,0.08)",
              border: "1px solid rgba(124,58,237,0.18)",
              color: "#a78bfa",
            }}
          >
            <ExternalLink size={12} /> Explorer
          </motion.button>
          {isActive && (
            <motion.button
              onClick={onRevoke}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              style={{
                ...styles.actBtn,
                background: "rgba(244,63,94,0.08)",
                border: "1px solid rgba(244,63,94,0.18)",
                color: "#fb7185",
              }}
            >
              <Ban size={12} /> Revoke
            </motion.button>
          )}
          {(isExpired || isRevoked) && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              style={{
                ...styles.actBtn,
                background: "rgba(16,185,129,0.08)",
                border: "1px solid rgba(16,185,129,0.18)",
                color: "#34d399",
              }}
            >
              <RotateCcw size={12} /> Renew
            </motion.button>
          )}
        </div>
      </div>
    </motion.div>
  );
});

function getTimelinePercent(grantedAt: string, expiresAt: string): number {
  if (!grantedAt || !expiresAt) return 0;
  const start = new Date(grantedAt).getTime();
  const end = new Date(expiresAt).getTime();
  const now = Date.now();
  const total = end - start;
  const elapsed = now - start;
  return Math.min(Math.max((elapsed / total) * 100, 0), 100);
}

const styles: Record<string, React.CSSProperties> = {
  pageHdr: {
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    marginBottom: 28,
  },
  pageTitle: {
    fontFamily: "'Syne', sans-serif",
    fontSize: 26,
    fontWeight: 800,
    color: "#ede9ff",
    letterSpacing: "-0.5px",
    marginBottom: 4,
  },
  pageSub: { fontSize: 13, color: "#5a5480" },
  hdrActions: { display: "flex", gap: 8 },
  btnSecondary: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "8px 16px",
    borderRadius: 10,
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    fontSize: 12,
    fontWeight: 600,
    color: "#9d96c8",
    cursor: "pointer",
    fontFamily: "'DM Sans', sans-serif",
  },
  btnPrimary: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "8px 16px",
    borderRadius: 10,
    background: "linear-gradient(135deg, #7c3aed, #9333ea)",
    border: "1px solid rgba(139,92,246,0.4)",
    fontSize: 12,
    fontWeight: 600,
    color: "white",
    cursor: "pointer",
    fontFamily: "'DM Sans', sans-serif",
    boxShadow: "0 4px 16px rgba(124,58,237,0.3)",
  },
  statsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: 12,
    marginBottom: 24,
  },
  statCard: {
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 16,
    padding: "20px 20px 18px",
    position: "relative",
    overflow: "hidden",
    transition: "all 0.25s ease",
  },
  statGlow: {
    position: "absolute",
    width: 80,
    height: 80,
    borderRadius: "50%",
    filter: "blur(30px)",
    top: -10,
    right: -10,
    opacity: 0.15,
  },
  statLabel: {
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: "0.05em",
    textTransform: "uppercase",
    color: "#5a5480",
    marginBottom: 10,
    display: "flex",
    alignItems: "center",
    gap: 6,
  },
  statDot: { width: 6, height: 6, borderRadius: "50%" },
  statNum: {
    fontFamily: "'Syne', sans-serif",
    fontSize: 36,
    fontWeight: 800,
    lineHeight: 1,
    marginBottom: 6,
  },
  statTrend: { fontSize: 11, color: "#5a5480" },
  toolbar: { display: "flex", alignItems: "center", gap: 10, marginBottom: 16 },
  searchBar: {
    flex: 1,
    display: "flex",
    alignItems: "center",
    gap: 10,
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 12,
    padding: "10px 16px",
    transition: "all 0.25s",
  },
  searchInput: {
    background: "none",
    border: "none",
    outline: "none",
    fontSize: 13,
    color: "#ede9ff",
    width: "100%",
    fontFamily: "'DM Sans', sans-serif",
  },
  filterBtn: {
    display: "flex",
    alignItems: "center",
    gap: 7,
    padding: "10px 16px",
    borderRadius: 12,
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    fontSize: 12,
    fontWeight: 600,
    color: "#9d96c8",
    cursor: "pointer",
    whiteSpace: "nowrap",
  },
  filterBtnActive: {
    background: "rgba(124,58,237,0.15)",
    borderColor: "rgba(139,92,246,0.3)",
    color: "#a78bfa",
  },
  viewToggle: {
    display: "flex",
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 10,
    overflow: "hidden",
  },
  viewBtn: {
    width: 36,
    height: 36,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    color: "#5a5480",
    transition: "all 0.2s",
  },
  viewBtnActive: { background: "rgba(124,58,237,0.15)", color: "#a78bfa" },
  filterChips: { display: "flex", gap: 6, marginBottom: 16, flexWrap: "wrap" },
  chip: {
    padding: "5px 12px",
    borderRadius: 100,
    fontSize: 11,
    fontWeight: 600,
    border: "1px solid rgba(255,255,255,0.07)",
    background: "rgba(255,255,255,0.04)",
    color: "#5a5480",
    cursor: "pointer",
    transition: "all 0.2s",
  },
  chipActive: {
    background: "rgba(124,58,237,0.15)",
    borderColor: "rgba(124,58,237,0.3)",
    color: "#a78bfa",
  },
  loadingContainer: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    minHeight: "40vh",
  },
  spinner: {
    width: 40,
    height: 40,
    border: "3px solid rgba(255,255,255,0.07)",
    borderTopColor: "#7c3aed",
    borderRadius: "50%",
  },
  emptyState: {
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 20,
    padding: "64px 40px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    textAlign: "center",
    position: "relative",
    overflow: "hidden",
  },
  emptyIcon: {
    width: 80,
    height: 80,
    borderRadius: 22,
    background: "rgba(124,58,237,0.08)",
    border: "1px solid rgba(124,58,237,0.15)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 20,
    boxShadow: "0 0 30px rgba(124,58,237,0.1)",
    color: "#a78bfa",
  },
  emptyTitle: {
    fontFamily: "'Syne', sans-serif",
    fontSize: 20,
    fontWeight: 700,
    color: "#ede9ff",
    marginBottom: 8,
  },
  emptySub: {
    fontSize: 13,
    color: "#5a5480",
    maxWidth: 280,
    lineHeight: 1.6,
    marginBottom: 24,
  },
  emptyHint: {
    background: "rgba(124,58,237,0.06)",
    border: "1px solid rgba(124,58,237,0.12)",
    borderRadius: 12,
    padding: "12px 20px",
    fontSize: 12,
    color: "#9d96c8",
    maxWidth: 340,
    lineHeight: 1.6,
  },
  consentList: { display: "flex", flexDirection: "column", gap: 10 },
  consentCard: {
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderLeft: "3px solid",
    borderRadius: 16,
    padding: "18px 20px",
    display: "flex",
    alignItems: "flex-start",
    gap: 16,
    transition: "all 0.25s ease",
    cursor: "pointer",
    position: "relative",
    overflow: "hidden",
  },
  consentIcon: {
    width: 42,
    height: 42,
    borderRadius: 12,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 20,
    flexShrink: 0,
  },
  consentBody: { flex: 1, minWidth: 0 },
  consentTop: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 4,
  },
  consentOrg: {
    fontFamily: "'Syne', sans-serif",
    fontSize: 14,
    fontWeight: 700,
    color: "#ede9ff",
  },
  statusBadge: {
    display: "flex",
    alignItems: "center",
    gap: 4,
    padding: "2px 8px",
    borderRadius: 100,
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: "0.03em",
  },
  statusDot: { width: 5, height: 5, borderRadius: "50%" },
  consentPurpose: { fontSize: 12, color: "#5a5480", marginBottom: 6 },
  consentTags: { display: "flex", gap: 4, flexWrap: "wrap" },
  tag: {
    padding: "2px 7px",
    borderRadius: 6,
    fontSize: 10,
    fontWeight: 500,
    color: "#5a5480",
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
  },
  timelineBar: { marginTop: 8, display: "flex", gap: 6, alignItems: "center" },
  tlLabel: { fontSize: 9, color: "#5a5480", whiteSpace: "nowrap" },
  tlTrack: {
    flex: 1,
    height: 3,
    background: "rgba(255,255,255,0.05)",
    borderRadius: 100,
    overflow: "hidden",
  },
  tlFill: { height: "100%", borderRadius: 100, transition: "width 0.8s ease" },
  consentMeta: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-end",
    gap: 8,
    flexShrink: 0,
  },
  consentHash: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 10,
    color: "#5a5480",
    background: "rgba(255,255,255,0.03)",
    padding: "3px 8px",
    borderRadius: 6,
    border: "1px solid rgba(255,255,255,0.07)",
  },
  consentDate: { fontSize: 10, color: "#5a5480" },
  consentActions: { display: "flex", gap: 6 },
  actBtn: {
    display: "flex",
    alignItems: "center",
    gap: 4,
    padding: "4px 10px",
    borderRadius: 8,
    fontSize: 10,
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  pagination: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 20,
  },
  pageInfo: { fontSize: 12, color: "#5a5480" },
  pageBtns: { display: "flex", gap: 6 },
  pgBtn: {
    width: 32,
    height: 32,
    borderRadius: 8,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 600,
    color: "#9d96c8",
    transition: "all 0.2s",
  },
  pgBtnActive: {
    background: "rgba(124,58,237,0.15)",
    borderColor: "rgba(124,58,237,0.3)",
    color: "#a78bfa",
  },
};
