import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useWallet } from "../hooks/useWallet";
import api from "../lib/api";

interface Fiduciary {
  id: string;
  name: string;
  registration_number: string;
  data_categories: string[];
  purposes: string[];
  compliance_status: string;
  created_at: string;
}

export default function Fiduciaries() {
  const { address } = useWallet();
  const [fiduciaries, setFiduciaries] = useState<Fiduciary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadFiduciaries();
  }, [address]);

  const loadFiduciaries = async () => {
    try {
      setLoading(true);
      const response = await api.get("/api/v1/public/fiduciaries");
      if (response.data.success) {
        setFiduciaries(response.data.data.fiduciaries);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load fiduciaries");
    } finally {
      setLoading(false);
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
    grid: {
      display: "grid",
      gridTemplateColumns: "repeat(auto-fill, minmax(350px, 1fr))",
      gap: 20,
    },
    card: {
      background: "rgba(18,12,38,0.85)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: 20,
      padding: 24,
      backdropFilter: "blur(16px)",
    },
    cardHeader: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: 16,
    },
    cardTitle: {
      fontSize: 18,
      fontWeight: 600,
      color: "#f1f0ff",
    },
    status: {
      padding: "4px 12px",
      borderRadius: 100,
      fontSize: 12,
      fontWeight: 500,
    },
    statusActive: {
      background: "rgba(16,185,129,0.15)",
      color: "#6ee7b7",
    },
    statusInactive: {
      background: "rgba(239,68,68,0.15)",
      color: "#fca5a5",
    },
    meta: {
      fontSize: 13,
      color: "#6b6690",
      marginBottom: 12,
    },
    tags: {
      display: "flex",
      flexWrap: "wrap",
      gap: 8,
      marginTop: 12,
    },
    tag: {
      padding: "4px 10px",
      background: "rgba(139,92,246,0.15)",
      borderRadius: 6,
      fontSize: 12,
      color: "#c4b5fd",
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
  };

  if (loading) {
    return <div style={styles.loading}>Loading fiduciaries...</div>;
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
        <h1 style={styles.title}>Data Fiduciaries</h1>
        <p style={styles.subtitle}>
          Organizations registered to collect and process your data
        </p>
      </motion.div>

      {fiduciaries.length === 0 ? (
        <div style={styles.empty}>No fiduciaries found</div>
      ) : (
        <div style={styles.grid}>
          {fiduciaries.map((fiduciary, index) => (
            <motion.div
              key={fiduciary.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              style={styles.card}
            >
              <div style={styles.cardHeader}>
                <span style={styles.cardTitle}>{fiduciary.name}</span>
                <span
                  style={{
                    ...styles.status,
                    ...(fiduciary.compliance_status === "ACTIVE"
                      ? styles.statusActive
                      : styles.statusInactive),
                  }}
                >
                  {fiduciary.compliance_status}
                </span>
              </div>
              <div style={styles.meta}>
                Reg: {fiduciary.registration_number}
              </div>
              {fiduciary.purposes && fiduciary.purposes.length > 0 && (
                <div style={styles.tags}>
                  {fiduciary.purposes.map((purpose) => (
                    <span key={purpose} style={styles.tag}>
                      {purpose}
                    </span>
                  ))}
                </div>
              )}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
