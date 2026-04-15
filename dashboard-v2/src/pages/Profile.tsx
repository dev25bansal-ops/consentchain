import { useState } from "react";
import { motion } from "framer-motion";
import { useWallet } from "../hooks/useWallet";

export default function Profile() {
  const { address, disconnect } = useWallet();
  const [copied, setCopied] = useState(false);

  const copyAddress = () => {
    if (address) {
      navigator.clipboard.writeText(address);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const styles: Record<string, React.CSSProperties> = {
    container: {
      padding: 24,
      maxWidth: 600,
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
    card: {
      background: "rgba(18,12,38,0.85)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: 20,
      padding: 32,
      backdropFilter: "blur(16px)",
      marginBottom: 24,
    },
    avatar: {
      width: 80,
      height: 80,
      borderRadius: "50%",
      background: "linear-gradient(135deg, #4c26c8, #7c3aed)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: 32,
      margin: "0 auto 24px",
    },
    walletSection: {
      marginBottom: 24,
    },
    label: {
      fontSize: 12,
      fontWeight: 600,
      color: "#6b6690",
      textTransform: "uppercase",
      letterSpacing: "0.05em",
      marginBottom: 8,
    },
    addressBox: {
      display: "flex",
      alignItems: "center",
      gap: 12,
      background: "rgba(255,255,255,0.04)",
      borderRadius: 12,
      padding: 12,
    },
    address: {
      flex: 1,
      fontFamily: "monospace",
      fontSize: 13,
      color: "#a49ecf",
      wordBreak: "break-all",
    },
    copyBtn: {
      padding: "8px 12px",
      background: "rgba(139,92,246,0.2)",
      border: "none",
      borderRadius: 8,
      color: "#c4b5fd",
      cursor: "pointer",
      fontSize: 12,
      whiteSpace: "nowrap",
    },
    stats: {
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: 16,
      marginBottom: 24,
    },
    statItem: {
      textAlign: "center",
      padding: 16,
      background: "rgba(255,255,255,0.04)",
      borderRadius: 12,
    },
    statValue: {
      fontSize: 24,
      fontWeight: 700,
      color: "#f1f0ff",
      marginBottom: 4,
    },
    statLabel: {
      fontSize: 12,
      color: "#6b6690",
    },
    section: {
      marginBottom: 24,
    },
    sectionTitle: {
      fontSize: 16,
      fontWeight: 600,
      color: "#f1f0ff",
      marginBottom: 12,
    },
    infoRow: {
      display: "flex",
      justifyContent: "space-between",
      padding: "12px 0",
      borderBottom: "1px solid rgba(255,255,255,0.05)",
    },
    infoLabel: {
      color: "#6b6690",
      fontSize: 14,
    },
    infoValue: {
      color: "#f1f0ff",
      fontSize: 14,
    },
    disconnectBtn: {
      width: "100%",
      padding: 16,
      background: "rgba(239,68,68,0.1)",
      border: "1px solid rgba(239,68,68,0.3)",
      borderRadius: 12,
      color: "#fca5a5",
      fontSize: 14,
      fontWeight: 500,
      cursor: "pointer",
    },
  };

  return (
    <div style={styles.container}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        style={styles.header}
      >
        <h1 style={styles.title}>Profile</h1>
        <p style={styles.subtitle}>Manage your wallet and account settings</p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        style={styles.card}
      >
        <div style={styles.avatar}>👤</div>

        <div style={styles.walletSection}>
          <div style={styles.label}>Wallet Address</div>
          <div style={styles.addressBox}>
            <span style={styles.address}>{address}</span>
            <button onClick={copyAddress} style={styles.copyBtn}>
              {copied ? "✓ Copied" : "Copy"}
            </button>
          </div>
        </div>

        <div style={styles.stats}>
          <div style={styles.statItem}>
            <div style={styles.statValue}>-</div>
            <div style={styles.statLabel}>Consents</div>
          </div>
          <div style={styles.statItem}>
            <div style={styles.statValue}>-</div>
            <div style={styles.statLabel}>Active</div>
          </div>
          <div style={styles.statItem}>
            <div style={styles.statValue}>-</div>
            <div style={styles.statLabel}>Revoked</div>
          </div>
        </div>

        <div style={styles.section}>
          <div style={styles.sectionTitle}>Network</div>
          <div style={styles.infoRow}>
            <span style={styles.infoLabel}>Network</span>
            <span style={styles.infoValue}>Algorand Testnet</span>
          </div>
          <div style={styles.infoRow}>
            <span style={styles.infoLabel}>Chain</span>
            <span style={styles.infoValue}>Testnet</span>
          </div>
          <div style={styles.infoRow}>
            <span style={styles.infoLabel}>Status</span>
            <span style={{ ...styles.infoValue, color: "#6ee7b7" }}>
              Connected
            </span>
          </div>
        </div>

        <button
          onClick={disconnect}
          style={styles.disconnectBtn}
          onMouseOver={(e) => {
            e.currentTarget.style.background = "rgba(239,68,68,0.2)";
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.background = "rgba(239,68,68,0.1)";
          }}
        >
          Disconnect Wallet
        </button>
      </motion.div>
    </div>
  );
}
