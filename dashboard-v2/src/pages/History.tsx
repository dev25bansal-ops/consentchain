import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useWallet } from "../hooks/useWallet";
import api from "../lib/api";

interface Consent {
  consent_id: string;
  purpose: string;
  status: string;
  granted_at: string;
  expires_at: string | null;
  revoked_at: string | null;
  consent_hash: string;
}

export default function History() {
  const { address } = useWallet();
  const [consents, setConsents] = useState<Consent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");

  useEffect(() => {
    loadHistory();
  }, [address, statusFilter]);

  const loadHistory = async () => {
    if (!address) return;
    try {
      setLoading(true);
      const response = await api.get(`/api/v1/public/consent/${address}`, {
        params: { status: statusFilter || undefined },
      });
      if (response.data.success) {
        setConsents(response.data.data.consents);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load history");
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "GRANTED":
        return { bg: "rgba(16,185,129,0.15)", color: "#6ee7b7" };
      case "REVOKED":
        return { bg: "rgba(239,68,68,0.15)", color: "#fca5a5" };
      case "EXPIRED":
        return { bg: "rgba(245,158,11,0.15)", color: "#fcd34d" };
      default:
        return { bg: "rgba(139,92,246,0.15)", color: "#c4b5fd" };
    }
  };

  const styles: Record<string, React.CSSProperties> = {
    container: {
      padding: 24,
      maxWidth: 1200,
      margin: "0 auto",
    },
    header: {
      marginBottom: 32,
    },
    title: {
      fontSize: 32,
      fontWeight: 700,
      color: "#f1f0ff",
      marginBottom: 8,
    },
    subtitle: {
      fontSize: 16,
      color: "#6b6690",
    },
    filters: {
      display: "flex",
      gap: 12,
      marginBottom: 24,
      flexWrap: "wrap",
    },
    filterBtn: {
      padding: "8px 16px",
      borderRadius: 100,
      border: "1px solid rgba(255,255,255,0.1)",
      background: "rgba(255,255,255,0.05)",
      color: "#a49ecf",
      cursor: "pointer",
      fontSize: 14,
    },
    filterBtnActive: {
      background: "linear-gradient(135deg, #4c26c8, #7c3aed)",
      borderColor: "rgba(139,92,246,0.5)",
      color: "#f1f0ff",
    },
    table: {
      width: "100%",
      borderCollapse: "collapse",
      background: "rgba(18,12,38,0.85)",
      borderRadius: 20,
      overflow: "hidden",
    },
    th: {
      padding: "16px 20px",
      textAlign: "left",
      fontSize: 13,
      fontWeight: 600,
      color: "#6b6690",
      borderBottom: "1px solid rgba(255,255,255,0.05)",
      textTransform: "uppercase",
      letterSpacing: "0.05em",
    },
    td: {
      padding: "16px 20px",
      fontSize: 14,
      color: "#f1f0ff",
      borderBottom: "1px solid rgba(255,255,255,0.03)",
    },
    status: {
      padding: "4px 12px",
      borderRadius: 100,
      fontSize: 12,
      fontWeight: 500,
      display: "inline-block",
    },
    loading: {
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      height: 300,
      color: "#6b6690",
    },
    error: {
      background: "rgba(239,68,68,0.1)",
      border: "1px solid rgba(239,68,68,0.3)",
      borderRadius: 12,
      padding: 16,
      color: "#fca5a5",
      textAlign: "center",
    },
    empty: {
      textAlign: "center",
      padding: 48,
      color: "#6b6690",
    },
    purpose: {
      fontWeight: 500,
    },
    hash: {
      fontFamily: "monospace",
      fontSize: 12,
      color: "#6b6690",
    },
  };

  if (loading) {
    return <div style={styles.loading}>Loading consent history...</div>;
  }

  if (error) {
    return (
      <div style={styles.container}>
        <div style={styles.error}>{error}</div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        style={styles.header}
      >
        <h1 style={styles.title}>Consent History</h1>
        <p style={styles.subtitle}>
          Complete history of all your consent records
        </p>
      </motion.div>

      <div style={styles.filters}>
        {["", "GRANTED", "REVOKED", "EXPIRED"].map((status) => (
          <button
            key={status}
            onClick={() => setStatusFilter(status)}
            style={{
              ...styles.filterBtn,
              ...(statusFilter === status ? styles.filterBtnActive : {}),
            }}
          >
            {status || "All"}
          </button>
        ))}
      </div>

      {consents.length === 0 ? (
        <div style={styles.empty}>No consent history found</div>
      ) : (
        <motion.table
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={styles.table}
        >
          <thead>
            <tr>
              <th style={styles.th}>Purpose</th>
              <th style={styles.th}>Status</th>
              <th style={styles.th}>Granted</th>
              <th style={styles.th}>Expires</th>
              <th style={styles.th}>Hash</th>
            </tr>
          </thead>
          <tbody>
            {consents.map((consent) => {
              const statusStyle = getStatusColor(consent.status);
              return (
                <tr key={consent.consent_id}>
                  <td style={{ ...styles.td, ...styles.purpose }}>
                    {consent.purpose}
                  </td>
                  <td style={styles.td}>
                    <span
                      style={{
                        ...styles.status,
                        background: statusStyle.bg,
                        color: statusStyle.color,
                      }}
                    >
                      {consent.status}
                    </span>
                  </td>
                  <td style={styles.td}>{formatDate(consent.granted_at)}</td>
                  <td style={styles.td}>{formatDate(consent.expires_at)}</td>
                  <td style={styles.td}>
                    <span style={styles.hash}>
                      {consent.consent_hash.slice(0, 12)}...
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </motion.table>
      )}
    </div>
  );
}
