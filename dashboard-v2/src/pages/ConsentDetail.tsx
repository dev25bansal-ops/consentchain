import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  ExternalLink,
  Shield,
  Loader2,
  Clock,
  Hash,
  User,
  Building2,
} from "lucide-react";
import { format } from "date-fns";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import api from "../lib/api";
import { fadeInUp, staggerContainer, staggerItem } from "../lib/animations";

interface ConsentDetail {
  consent_id: string;
  principal_id: string;
  fiduciary_id: string;
  purpose: string;
  data_types: string[];
  status: string;
  granted_at: string;
  expires_at: string;
  consent_hash: string;
  on_chain_tx_id: string;
}

interface ConsentEvent {
  event_id: string;
  event_type: string;
  actor: string;
  new_status: string;
  created_at: string;
  tx_id: string;
}

export default function ConsentDetail() {
  const { id } = useParams();
  const [consent, setConsent] = useState<ConsentDetail | null>(null);
  const [events, setEvents] = useState<ConsentEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadConsentDetail();
  }, [id]);

  async function loadConsentDetail() {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const [consentRes, historyRes] = await Promise.all([
        api.get(`/api/v1/consent/${id}`),
        api
          .get(`/api/v1/consent/${id}/history`)
          .catch(() => ({ data: { data: { events: [] } } })),
      ]);

      const consent = consentRes.data?.data;

      if (consent) {
        setConsent(consent);
      } else {
        setError("Consent not found");
      }

      setEvents(historyRes.data?.data?.events || []);
    } catch (err) {
      console.error("Failed to load consent detail:", err);
      setError("Failed to load consent details");
    } finally {
      setLoading(false);
    }
  }

  async function verifyConsent() {
    if (!consent) return;
    try {
      const response = await api.post("/api/v1/consent/verify", {
        consent_id: consent.consent_id,
        principal_id: consent.principal_id,
      });
      if (response.data.success) {
        alert("Consent verified successfully on-chain!");
      } else {
        alert(`Verification failed: ${response.data.message}`);
      }
    } catch (err) {
      console.error("Verification failed:", err);
      alert("Failed to verify consent");
    }
  }

  const getStatusStyles = (status: string) => {
    const styles: Record<
      string,
      { bg: string; border: string; color: string }
    > = {
      GRANTED: {
        bg: "rgba(16,185,129,0.1)",
        border: "rgba(16,185,129,0.3)",
        color: "#34d399",
      },
      REVOKED: {
        bg: "rgba(244,63,94,0.1)",
        border: "rgba(244,63,94,0.3)",
        color: "#fb7185",
      },
      EXPIRED: {
        bg: "rgba(245,158,11,0.1)",
        border: "rgba(245,158,11,0.3)",
        color: "#fbbf24",
      },
      PENDING: {
        bg: "rgba(59,130,246,0.1)",
        border: "rgba(59,130,246,0.3)",
        color: "#60a5fa",
      },
      MODIFIED: {
        bg: "rgba(124,58,237,0.1)",
        border: "rgba(124,58,237,0.3)",
        color: "#a78bfa",
      },
    };
    return styles[status] || styles.PENDING;
  };

  if (loading) {
    return (
      <div style={styles.loadingContainer}>
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        >
          <Loader2 size={40} color="#7c3aed" />
        </motion.div>
      </div>
    );
  }

  if (error || !consent) {
    return (
      <div>
        <motion.div variants={fadeInUp} initial="initial" animate="animate">
          <Link to="/" style={styles.backLink}>
            <ArrowLeft size={16} />
            Back to Consents
          </Link>
        </motion.div>
        <motion.div
          variants={fadeInUp}
          initial="initial"
          animate="animate"
          style={styles.card}
        >
          <p style={{ color: "#fb7185", textAlign: "center" }}>
            {error || "Consent not found"}
          </p>
        </motion.div>
      </div>
    );
  }

  const statusStyle = getStatusStyles(consent.status);

  return (
    <div>
      <motion.div variants={fadeInUp} initial="initial" animate="animate">
        <Link to="/" style={styles.backLink}>
          <ArrowLeft size={16} />
          Back to Consents
        </Link>
      </motion.div>

      <motion.div
        variants={fadeInUp}
        initial="initial"
        animate="animate"
        style={styles.card}
      >
        <div style={styles.cardHeader}>
          <div>
            <h1 style={styles.pageTitle}>Consent Details</h1>
            <p style={styles.consentId}>{id}</p>
          </div>
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            style={{
              ...styles.statusBadge,
              background: statusStyle.bg,
              border: `1px solid ${statusStyle.border}`,
              color: statusStyle.color,
            }}
          >
            {consent.status}
          </motion.div>
        </div>

        <div style={styles.grid}>
          <motion.div
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            style={styles.column}
          >
            <DetailItem
              icon={<Building2 size={18} color="#7c3aed" />}
              label="Purpose"
              value={consent.purpose}
            />
            <div style={styles.detailItem}>
              <label style={styles.label}>Data Types</label>
              <div style={styles.tags}>
                {consent.data_types.map((type) => (
                  <motion.span
                    key={type}
                    variants={staggerItem}
                    style={styles.tag}
                  >
                    {type.replace(/_/g, " ")}
                  </motion.span>
                ))}
              </div>
            </div>
            <DetailItem
              icon={<Clock size={18} color="#22d3ee" />}
              label="Granted At"
              value={
                consent.granted_at
                  ? format(new Date(consent.granted_at), "PPP")
                  : "N/A"
              }
            />
            <DetailItem
              icon={<Clock size={18} color="#f59e0b" />}
              label="Expires At"
              value={
                consent.expires_at
                  ? format(new Date(consent.expires_at), "PPP")
                  : "No expiry"
              }
            />
          </motion.div>

          <motion.div
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            style={styles.column}
          >
            <div style={styles.detailItem}>
              <label style={styles.label}>On-Chain Transaction</label>
              {consent.on_chain_tx_id ? (
                <motion.a
                  href={`https://testnet.algoscan.app/tx/${consent.on_chain_tx_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  whileHover={{ x: 3 }}
                  style={styles.link}
                >
                  View on Algoscan
                  <ExternalLink size={14} />
                </motion.a>
              ) : (
                <p style={styles.muted}>Not recorded on-chain</p>
              )}
            </div>
            <div style={styles.detailItem}>
              <label style={styles.label}>Consent Hash</label>
              <div style={styles.codeBox}>
                <Hash size={14} color="#5a5480" />
                <code style={styles.code}>{consent.consent_hash}</code>
              </div>
            </div>
            <div style={styles.detailItem}>
              <label style={styles.label}>Principal ID</label>
              <div style={styles.codeBox}>
                <User size={14} color="#5a5480" />
                <code style={styles.code}>{consent.principal_id}</code>
              </div>
            </div>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          style={styles.actions}
        >
          <motion.button
            onClick={verifyConsent}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            style={styles.verifyBtn}
          >
            <Shield size={16} />
            Verify On-Chain
          </motion.button>
          <Link to="/" style={styles.backBtn}>
            Back to List
          </Link>
        </motion.div>
      </motion.div>

      <motion.div
        variants={fadeInUp}
        initial="initial"
        animate="animate"
        transition={{ delay: 0.1 }}
        style={styles.card}
      >
        <h2 style={styles.sectionTitle}>Event History</h2>
        {events.length === 0 ? (
          <p
            style={{ ...styles.muted, textAlign: "center", padding: "2rem 0" }}
          >
            No events recorded
          </p>
        ) : (
          <motion.div
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            style={styles.eventList}
          >
            {events.map((event, index) => (
              <motion.div
                key={event.event_id}
                variants={staggerItem}
                whileHover={{ x: 4 }}
                style={styles.eventItem}
              >
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: index * 0.1 }}
                  style={styles.eventIcon}
                >
                  <Shield size={20} color="#10b981" />
                </motion.div>
                <div style={{ flex: 1 }}>
                  <p style={styles.eventType}>
                    {event.event_type.replace(/_/g, " ")}
                  </p>
                  <p style={styles.eventDate}>
                    {event.created_at
                      ? format(new Date(event.created_at), "PPP pp")
                      : "N/A"}
                  </p>
                  {event.tx_id && (
                    <p style={styles.eventTx}>TX: {event.tx_id}</p>
                  )}
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}

function DetailItem({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <motion.div variants={staggerItem} style={styles.detailItem}>
      <label style={styles.label}>
        {icon}
        {label}
      </label>
      <p style={styles.value}>{value}</p>
    </motion.div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  loadingContainer: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "4rem 0",
  },
  backLink: {
    display: "inline-flex",
    alignItems: "center",
    gap: "0.5rem",
    color: "#9d96c8",
    textDecoration: "none",
    fontSize: "0.875rem",
    marginBottom: "1.5rem",
  },
  card: {
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 16,
    padding: "1.5rem",
    marginBottom: "1.5rem",
  },
  cardHeader: {
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    marginBottom: "2rem",
  },
  pageTitle: {
    fontFamily: "'Syne', sans-serif",
    fontSize: 26,
    fontWeight: 800,
    color: "#ede9ff",
    letterSpacing: "-0.5px",
  },
  consentId: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: "0.8rem",
    color: "#5a5480",
    marginTop: "0.25rem",
  },
  statusBadge: {
    padding: "0.5rem 1rem",
    borderRadius: 100,
    fontSize: "0.75rem",
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
    gap: "2rem",
  },
  column: {
    display: "flex",
    flexDirection: "column",
    gap: "1.25rem",
  },
  detailItem: {
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
  },
  label: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    fontSize: "0.75rem",
    color: "#5a5480",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  value: {
    fontSize: "1rem",
    fontWeight: 500,
    color: "#ede9ff",
  },
  tags: {
    display: "flex",
    flexWrap: "wrap",
    gap: "0.5rem",
  },
  tag: {
    padding: "0.375rem 0.75rem",
    background: "rgba(124,58,237,0.1)",
    border: "1px solid rgba(124,58,237,0.2)",
    borderRadius: 100,
    fontSize: "0.75rem",
    color: "#a78bfa",
  },
  link: {
    display: "inline-flex",
    alignItems: "center",
    gap: "0.5rem",
    color: "#7c3aed",
    textDecoration: "none",
    fontWeight: 500,
    fontSize: "0.9rem",
  },
  muted: {
    color: "#5a5480",
    fontSize: "0.9rem",
  },
  codeBox: {
    display: "flex",
    alignItems: "flex-start",
    gap: "0.5rem",
    background: "rgba(255,255,255,0.03)",
    padding: "0.75rem",
    borderRadius: 8,
    border: "1px solid rgba(255,255,255,0.05)",
  },
  code: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: "0.8rem",
    color: "#9d96c8",
    wordBreak: "break-all",
  },
  actions: {
    display: "flex",
    gap: "0.75rem",
    marginTop: "2rem",
    paddingTop: "1.5rem",
    borderTop: "1px solid rgba(255,255,255,0.05)",
  },
  verifyBtn: {
    display: "inline-flex",
    alignItems: "center",
    gap: "0.5rem",
    padding: "0.75rem 1.25rem",
    background: "linear-gradient(135deg, #4c26c8, #7c3aed)",
    border: "none",
    borderRadius: 10,
    color: "white",
    fontWeight: 600,
    fontSize: "0.875rem",
    cursor: "pointer",
  },
  backBtn: {
    display: "inline-flex",
    alignItems: "center",
    gap: "0.5rem",
    padding: "0.75rem 1.25rem",
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 10,
    color: "#9d96c8",
    textDecoration: "none",
    fontWeight: 500,
    fontSize: "0.875rem",
  },
  sectionTitle: {
    fontFamily: "'Syne', sans-serif",
    fontWeight: 600,
    fontSize: "1.125rem",
    color: "#ede9ff",
    marginBottom: "1.25rem",
  },
  eventList: {
    display: "flex",
    flexDirection: "column",
    gap: "0.75rem",
  },
  eventItem: {
    display: "flex",
    alignItems: "flex-start",
    gap: "1rem",
    padding: "1rem",
    background: "rgba(255,255,255,0.03)",
    borderRadius: 12,
    border: "1px solid rgba(255,255,255,0.05)",
    cursor: "pointer",
  },
  eventIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    background: "rgba(16,185,129,0.1)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  eventType: {
    fontWeight: 500,
    color: "#ede9ff",
    marginBottom: "0.25rem",
  },
  eventDate: {
    fontSize: "0.8rem",
    color: "#5a5480",
  },
  eventTx: {
    fontSize: "0.7rem",
    color: "#5a5480",
    fontFamily: "'JetBrains Mono', monospace",
    marginTop: "0.25rem",
  },
};
