import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useWallet } from "../hooks/useWallet";
import api from "../lib/api";

interface Activity {
  id: string;
  action: string;
  resource_type: string;
  created_at: string;
  on_chain_reference?: string;
}

export default function Activity() {
  const { address } = useWallet();
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadActivity();
  }, [address]);

  const loadActivity = async () => {
    if (!address) return;
    try {
      setLoading(true);
      const response = await api.get(`/api/v1/public/consent/${address}`);
      if (response.data.success) {
        const consents = response.data.data.consents || [];
        const activityList: Activity[] = consents.map((c: any) => ({
          id: c.consent_id,
          action:
            c.status === "GRANTED"
              ? "Consent Granted"
              : c.status === "REVOKED"
                ? "Consent Revoked"
                : c.status === "EXPIRED"
                  ? "Consent Expired"
                  : "Consent Modified",
          resource_type: "consent",
          created_at: c.granted_at || c.revoked_at || new Date().toISOString(),
          on_chain_reference: c.consent_hash,
        }));
        setActivities(activityList);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load activity");
    } finally {
      setLoading(false);
    }
  };

  const getActionIcon = (action: string) => {
    if (action.includes("Granted")) return "✅";
    if (action.includes("Revoked")) return "❌";
    if (action.includes("Expired")) return "⏰";
    return "📝";
  };

  const getActionColor = (action: string) => {
    if (action.includes("Granted")) return "#6ee7b7";
    if (action.includes("Revoked")) return "#fca5a5";
    if (action.includes("Expired")) return "#fcd34d";
    return "#c4b5fd";
  };

  const formatRelativeTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor(diff / (1000 * 60));

    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return "Just now";
  };

  const styles: Record<string, React.CSSProperties> = {
    container: {
      padding: 24,
      maxWidth: 900,
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
    timeline: {
      position: "relative",
      paddingLeft: 32,
    },
    line: {
      position: "absolute",
      left: 15,
      top: 0,
      bottom: 0,
      width: 2,
      background: "rgba(255,255,255,0.08)",
    },
    item: {
      position: "relative",
      marginBottom: 24,
    },
    dot: {
      position: "absolute",
      left: -24,
      top: 4,
      width: 16,
      height: 16,
      borderRadius: "50%",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: 10,
    },
    card: {
      background: "rgba(18,12,38,0.85)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: 16,
      padding: 20,
      backdropFilter: "blur(16px)",
    },
    cardHeader: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: 8,
    },
    action: {
      fontSize: 16,
      fontWeight: 600,
      color: "#f1f0ff",
    },
    time: {
      fontSize: 13,
      color: "#6b6690",
    },
    meta: {
      fontSize: 13,
      color: "#a49ecf",
    },
    hash: {
      fontFamily: "monospace",
      fontSize: 12,
      color: "#6b6690",
      marginTop: 8,
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
    return <div style={styles.loading}>Loading activity...</div>;
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
        <h1 style={styles.title}>Activity</h1>
        <p style={styles.subtitle}>Recent actions and events on your account</p>
      </motion.div>

      {activities.length === 0 ? (
        <div style={styles.empty}>No recent activity</div>
      ) : (
        <div style={styles.timeline}>
          <div style={styles.line} />
          {activities.map((activity, index) => (
            <motion.div
              key={activity.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              style={styles.item}
            >
              <div
                style={{
                  ...styles.dot,
                  background: `${getActionColor(activity.action)}20`,
                }}
              >
                {getActionIcon(activity.action)}
              </div>
              <div style={styles.card}>
                <div style={styles.cardHeader}>
                  <span style={styles.action}>{activity.action}</span>
                  <span style={styles.time}>
                    {formatRelativeTime(activity.created_at)}
                  </span>
                </div>
                <div style={styles.meta}>
                  {activity.resource_type.charAt(0).toUpperCase() +
                    activity.resource_type.slice(1)}
                </div>
                {activity.on_chain_reference && (
                  <div style={styles.hash}>
                    {activity.on_chain_reference.slice(0, 20)}...
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
