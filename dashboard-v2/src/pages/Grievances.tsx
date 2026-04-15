import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useWallet } from "../hooks/useWallet";
import { useToast } from "../hooks/useToast";
import api from "../lib/api";
import { format } from "date-fns";
import {
  AlertTriangle,
  Plus,
  RefreshCw,
  ChevronRight,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { staggerContainer, staggerItem, fadeInUp } from "../lib/animations";
import GrievanceModal from "../components/GrievanceModal";

interface Grievance {
  id: string;
  type: string;
  subject: string;
  status: string;
  priority: string;
  created_at: string;
  resolution?: string;
  resolution_date?: string;
}

export default function Grievances() {
  const { address } = useWallet();
  const { success } = useToast();
  const [grievances, setGrievances] = useState<Grievance[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    if (address) {
      loadGrievances();
    }
  }, [address]);

  async function loadGrievances() {
    if (!address) return;
    setLoading(true);
    try {
      const response = await api.get(`/api/v1/public/grievance/${address}`);
      setGrievances(response.data?.data?.grievances || []);
    } catch (err) {
      console.error("Failed to load grievances:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleRefresh() {
    setRefreshing(true);
    await loadGrievances();
    setTimeout(() => setRefreshing(false), 600);
  }

  function getStatusConfig(status: string) {
    const configs: Record<
      string,
      { color: string; bg: string; border: string; icon: any }
    > = {
      SUBMITTED: {
        color: "#60a5fa",
        bg: "rgba(59,130,246,0.1)",
        border: "rgba(59,130,246,0.2)",
        icon: Clock,
      },
      ACKNOWLEDGED: {
        color: "#a78bfa",
        bg: "rgba(124,58,237,0.1)",
        border: "rgba(124,58,237,0.2)",
        icon: CheckCircle,
      },
      IN_PROGRESS: {
        color: "#fbbf24",
        bg: "rgba(245,158,11,0.1)",
        border: "rgba(245,158,11,0.2)",
        icon: Loader2,
      },
      RESOLVED: {
        color: "#34d399",
        bg: "rgba(16,185,129,0.1)",
        border: "rgba(16,185,129,0.2)",
        icon: CheckCircle,
      },
      REJECTED: {
        color: "#fb7185",
        bg: "rgba(244,63,94,0.1)",
        border: "rgba(244,63,94,0.2)",
        icon: XCircle,
      },
      ESCALATED: {
        color: "#f43f5e",
        bg: "rgba(244,63,94,0.1)",
        border: "rgba(244,63,94,0.2)",
        icon: AlertCircle,
      },
    };
    return configs[status] || configs.SUBMITTED;
  }

  function getPriorityConfig(priority: string) {
    const configs: Record<string, { color: string; label: string }> = {
      LOW: { color: "#5a5480", label: "Low" },
      MEDIUM: { color: "#fbbf24", label: "Medium" },
      HIGH: { color: "#f97316", label: "High" },
      URGENT: { color: "#f43f5e", label: "Urgent" },
    };
    return configs[priority] || configs.MEDIUM;
  }

  const stats = {
    total: grievances.length,
    pending: grievances.filter(
      (g) =>
        g.status === "SUBMITTED" ||
        g.status === "ACKNOWLEDGED" ||
        g.status === "IN_PROGRESS",
    ).length,
    resolved: grievances.filter((g) => g.status === "RESOLVED").length,
  };

  return (
    <div>
      <motion.div
        variants={fadeInUp}
        initial="initial"
        animate="animate"
        style={styles.pageHdr}
      >
        <div>
          <h1 style={styles.pageTitle}>Grievances</h1>
          <p style={styles.pageSub}>
            File and track complaints under DPDP Act Section 13
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
            onClick={() => setShowModal(true)}
            whileHover={{ scale: 1.02, y: -1 }}
            whileTap={{ scale: 0.98 }}
            style={styles.btnWarning}
          >
            <Plus size={14} />
            New Grievance
          </motion.button>
        </div>
      </motion.div>

      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        style={styles.statsGrid}
      >
        <StatCard label="Total" value={stats.total} type="total" delay={0.05} />
        <StatCard
          label="Pending"
          value={stats.pending}
          type="pending"
          delay={0.1}
        />
        <StatCard
          label="Resolved"
          value={stats.resolved}
          type="resolved"
          delay={0.15}
        />
      </motion.div>

      {loading ? (
        <div style={styles.loadingContainer}>
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            style={styles.spinner}
          />
        </div>
      ) : grievances.length === 0 ? (
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
            <AlertTriangle size={36} color="#f59e0b" />
          </motion.div>
          <div style={styles.emptyTitle}>No grievances filed</div>
          <div style={styles.emptySub}>
            You haven't filed any grievances yet. Submit a complaint if you have
            concerns about how your data is being processed.
          </div>
          <motion.button
            onClick={() => setShowModal(true)}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            style={{ ...styles.btnWarning, marginTop: 24 }}
          >
            <Plus size={14} />
            File First Grievance
          </motion.button>
        </motion.div>
      ) : (
        <motion.div
          variants={staggerContainer}
          initial="initial"
          animate="animate"
          style={styles.grievanceList}
        >
          {grievances.map((grievance, index) => {
            const statusConfig = getStatusConfig(grievance.status);
            const priorityConfig = getPriorityConfig(grievance.priority);
            const StatusIcon = statusConfig.icon;

            return (
              <motion.div
                key={grievance.id}
                variants={staggerItem}
                transition={{ delay: index * 0.05 }}
                whileHover={{ y: -1 }}
                style={styles.grievanceCard}
              >
                <div
                  style={{
                    ...styles.statusIcon,
                    background: statusConfig.bg,
                    border: `1px solid ${statusConfig.border}`,
                  }}
                >
                  <StatusIcon size={20} color={statusConfig.color} />
                </div>

                <div style={styles.grievanceBody}>
                  <div style={styles.grievanceTop}>
                    <span style={styles.grievanceType}>
                      {grievance.type.replace(/_/g, " ")}
                    </span>
                    <span
                      style={{
                        ...styles.statusBadge,
                        background: statusConfig.bg,
                        color: statusConfig.color,
                        border: `1px solid ${statusConfig.border}`,
                      }}
                    >
                      {grievance.status}
                    </span>
                  </div>
                  <div style={styles.grievanceSubject}>{grievance.subject}</div>
                  <div style={styles.grievanceMeta}>
                    <span style={{ color: priorityConfig.color }}>
                      {priorityConfig.label} Priority
                    </span>
                    <span>•</span>
                    <span>
                      Filed{" "}
                      {format(new Date(grievance.created_at), "dd MMM yyyy")}
                    </span>
                  </div>

                  {grievance.resolution && (
                    <div style={styles.resolutionBox}>
                      <strong>Resolution:</strong> {grievance.resolution}
                    </div>
                  )}
                </div>

                <div style={styles.grievanceActions}>
                  <motion.div
                    whileHover={{ scale: 1.05 }}
                    style={styles.actionBtn}
                  >
                    <ChevronRight size={16} />
                  </motion.div>
                </div>
              </motion.div>
            );
          })}
        </motion.div>
      )}

      <GrievanceModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onSuccess={() => {
          loadGrievances();
          success("Success", "Grievance submitted successfully");
        }}
      />
    </div>
  );
}

function StatCard({
  label,
  value,
  type,
  delay,
}: {
  label: string;
  value: number;
  type: "total" | "pending" | "resolved";
  delay: number;
}) {
  const config = {
    total: { color: "#3b82f6" },
    pending: { color: "#f59e0b" },
    resolved: { color: "#10b981" },
  };

  return (
    <motion.div
      variants={staggerItem}
      transition={{ delay }}
      whileHover={{ y: -2 }}
      style={styles.statCard}
    >
      <div style={{ ...styles.statDot, background: config[type].color }} />
      <div style={styles.statLabel}>{label}</div>
      <div style={{ ...styles.statNum, color: config[type].color }}>
        {value}
      </div>
    </motion.div>
  );
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
  },
  btnWarning: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "8px 16px",
    borderRadius: 10,
    background: "linear-gradient(135deg, #f59e0b, #fbbf24)",
    border: "none",
    fontSize: 12,
    fontWeight: 600,
    color: "#0b0917",
    cursor: "pointer",
    boxShadow: "0 4px 16px rgba(245,158,11,0.3)",
  },
  statsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
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
  },
  statDot: { width: 8, height: 8, borderRadius: "50%", marginBottom: 10 },
  statLabel: {
    fontSize: 11,
    fontWeight: 600,
    color: "#5a5480",
    marginBottom: 6,
  },
  statNum: { fontFamily: "'Syne', sans-serif", fontSize: 32, fontWeight: 800 },
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
    borderTopColor: "#f59e0b",
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
  },
  emptyIcon: {
    width: 80,
    height: 80,
    borderRadius: 22,
    background: "rgba(245,158,11,0.1)",
    border: "1px solid rgba(245,158,11,0.2)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 20,
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
    maxWidth: 300,
    lineHeight: 1.6,
  },
  grievanceList: { display: "flex", flexDirection: "column", gap: 10 },
  grievanceCard: {
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 16,
    padding: "18px 20px",
    display: "flex",
    alignItems: "flex-start",
    gap: 16,
    cursor: "pointer",
    transition: "all 0.25s ease",
  },
  statusIcon: {
    width: 42,
    height: 42,
    borderRadius: 12,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  grievanceBody: { flex: 1, minWidth: 0 },
  grievanceTop: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 4,
  },
  grievanceType: {
    fontFamily: "'Syne', sans-serif",
    fontSize: 14,
    fontWeight: 700,
    color: "#ede9ff",
  },
  statusBadge: {
    padding: "2px 8px",
    borderRadius: 100,
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: "0.03em",
  },
  grievanceSubject: { fontSize: 12, color: "#9d96c8", marginBottom: 6 },
  grievanceMeta: { display: "flex", gap: 8, fontSize: 10, color: "#5a5480" },
  resolutionBox: {
    marginTop: 10,
    padding: 10,
    background: "rgba(16,185,129,0.08)",
    borderRadius: 8,
    fontSize: 12,
    color: "#34d399",
  },
  grievanceActions: { display: "flex", alignItems: "center" },
  actionBtn: {
    padding: 8,
    background: "rgba(255,255,255,0.04)",
    borderRadius: 8,
    color: "#5a5480",
  },
};
