import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useWallet } from "../hooks/useWallet";
import {
  Bell,
  Lock,
  Globe,
  Moon,
  Check,
  ChevronRight,
  ExternalLink,
  Copy,
  Wallet,
  LogOut,
} from "lucide-react";
import { staggerContainer, staggerItem, fadeInUp } from "../lib/animations";

export default function Settings() {
  const { address, disconnect } = useWallet();
  const [copied, setCopied] = useState(false);
  const [notifications, setNotifications] = useState({
    expiryReminders: true,
    revokeNotifications: true,
    marketing: false,
    securityAlerts: true,
  });
  const [privacy, setPrivacy] = useState({
    ipfsStorage: true,
    onChainVerification: true,
    dataSharing: false,
  });

  const copyAddress = () => {
    if (address) {
      navigator.clipboard.writeText(address);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div style={{ maxWidth: "800px" }}>
      <motion.div
        variants={fadeInUp}
        initial="initial"
        animate="animate"
        style={styles.pageHdr}
      >
        <div>
          <h1 style={styles.pageTitle}>Settings</h1>
          <p style={styles.pageSub}>
            Manage your account preferences and privacy settings
          </p>
        </div>
      </motion.div>

      <motion.div
        variants={fadeInUp}
        initial="initial"
        animate="animate"
        style={styles.card}
      >
        <div style={styles.cardHeader}>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            <motion.div
              whileHover={{ scale: 1.05, rotate: [0, -5, 5, 0] }}
              transition={{ duration: 0.3 }}
              style={styles.walletIcon}
            >
              <Wallet size={28} color="white" />
            </motion.div>
            <div>
              <h2 style={styles.cardTitle}>Wallet Connected</h2>
              <p style={styles.cardSubtext}>Algorand Testnet</p>
            </div>
          </div>
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            style={styles.statusBadge}
          >
            <motion.span
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              style={styles.statusDot}
            />
            Active
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          style={styles.addressBox}
        >
          <p style={styles.addressLabel}>Wallet Address</p>
          <div
            style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}
          >
            <code style={styles.addressCode}>{address}</code>
            <motion.button
              onClick={copyAddress}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              style={styles.copyBtn}
            >
              <AnimatePresence mode="wait">
                {copied ? (
                  <motion.div
                    key="check"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    exit={{ scale: 0 }}
                  >
                    <Check size={18} color="#10b981" />
                  </motion.div>
                ) : (
                  <motion.div
                    key="copy"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    exit={{ scale: 0 }}
                  >
                    <Copy size={18} color="#9d96c8" />
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.button>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          style={{ display: "flex", gap: "0.75rem" }}
        >
          <motion.a
            href={`https://testnet.algoscan.app/address/${address}`}
            target="_blank"
            rel="noopener noreferrer"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            style={styles.explorerBtn}
          >
            <ExternalLink size={16} />
            View on Explorer
          </motion.a>
          <motion.button
            onClick={disconnect}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            style={styles.disconnectBtn}
          >
            <LogOut size={16} />
            Disconnect Wallet
          </motion.button>
        </motion.div>
      </motion.div>

      <motion.div
        variants={fadeInUp}
        initial="initial"
        animate="animate"
        transition={{ delay: 0.1 }}
        style={styles.card}
      >
        <SectionHeader
          icon={Bell}
          label="Notifications"
          description="Configure how you receive alerts"
          color="#f59e0b"
          bg="rgba(245,158,11,0.1)"
        />
        <motion.div
          variants={staggerContainer}
          initial="initial"
          animate="animate"
          style={styles.toggleList}
        >
          <ToggleSwitch
            label="Consent expiry reminders"
            description="Get notified before your consents expire"
            checked={notifications.expiryReminders}
            onChange={(checked) =>
              setNotifications({ ...notifications, expiryReminders: checked })
            }
          />
          <ToggleSwitch
            label="Revoke notifications"
            description="Receive alerts when consents are revoked"
            checked={notifications.revokeNotifications}
            onChange={(checked) =>
              setNotifications({
                ...notifications,
                revokeNotifications: checked,
              })
            }
          />
          <ToggleSwitch
            label="Security alerts"
            description="Important security notifications"
            checked={notifications.securityAlerts}
            onChange={(checked) =>
              setNotifications({ ...notifications, securityAlerts: checked })
            }
          />
          <ToggleSwitch
            label="Marketing communications"
            description="Product updates and news"
            checked={notifications.marketing}
            onChange={(checked) =>
              setNotifications({ ...notifications, marketing: checked })
            }
          />
        </motion.div>
      </motion.div>

      <motion.div
        variants={fadeInUp}
        initial="initial"
        animate="animate"
        transition={{ delay: 0.2 }}
        style={styles.card}
      >
        <SectionHeader
          icon={Lock}
          label="Privacy"
          description="Control your data and privacy settings"
          color="#3b82f6"
          bg="rgba(59,130,246,0.1)"
        />
        <motion.div
          variants={staggerContainer}
          initial="initial"
          animate="animate"
          style={styles.toggleList}
        >
          <ToggleSwitch
            label="Store consent data on IPFS"
            description="Decentralized storage for enhanced security"
            checked={privacy.ipfsStorage}
            onChange={(checked) =>
              setPrivacy({ ...privacy, ipfsStorage: checked })
            }
          />
          <ToggleSwitch
            label="On-chain verification"
            description="Enable blockchain-based consent verification"
            checked={privacy.onChainVerification}
            onChange={(checked) =>
              setPrivacy({ ...privacy, onChainVerification: checked })
            }
          />
          <ToggleSwitch
            label="Anonymous analytics"
            description="Help improve ConsentChain anonymously"
            checked={privacy.dataSharing}
            onChange={(checked) =>
              setPrivacy({ ...privacy, dataSharing: checked })
            }
          />
        </motion.div>
      </motion.div>

      <motion.div
        variants={fadeInUp}
        initial="initial"
        animate="animate"
        transition={{ delay: 0.3 }}
        style={styles.card}
      >
        <SectionHeader
          icon={Globe}
          label="Preferences"
          description="Language and display settings"
          color="#9333ea"
          bg="rgba(147,51,234,0.1)"
        />
        <motion.div
          variants={staggerContainer}
          initial="initial"
          animate="animate"
          style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}
        >
          <SettingRow icon={Globe} label="Language" value="English" delay={0} />
          <SettingRow icon={Moon} label="Theme" value="Dark" delay={0.1} />
        </motion.div>
      </motion.div>
    </div>
  );
}

function SectionHeader({
  icon: Icon,
  label,
  description,
  color,
  bg,
}: {
  icon: any;
  label: string;
  description: string;
  color: string;
  bg: string;
}) {
  return (
    <div style={styles.sectionHeader}>
      <motion.div
        whileHover={{ rotate: [0, -10, 10, 0] }}
        transition={{ duration: 0.3 }}
        style={{ ...styles.sectionIcon, background: bg }}
      >
        <Icon size={20} color={color} />
      </motion.div>
      <div>
        <h2 style={styles.sectionTitle}>{label}</h2>
        <p style={styles.sectionDesc}>{description}</p>
      </div>
    </div>
  );
}

function ToggleSwitch({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <motion.div
      variants={staggerItem}
      whileHover={{ scale: 1.01 }}
      style={styles.toggleRow}
      onClick={() => onChange(!checked)}
    >
      <div>
        <p style={styles.toggleLabel}>{label}</p>
        <p style={styles.toggleDesc}>{description}</p>
      </div>
      <motion.div
        layout
        style={{
          ...styles.toggleTrack,
          background: checked ? "#7c3aed" : "rgba(255,255,255,0.1)",
        }}
      >
        <motion.div
          layout
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
          style={{ ...styles.toggleThumb, left: checked ? 22 : 2 }}
        />
      </motion.div>
    </motion.div>
  );
}

function SettingRow({
  icon: Icon,
  label,
  value,
  delay,
}: {
  icon: any;
  label: string;
  value: string;
  delay: number;
}) {
  return (
    <motion.div
      variants={staggerItem}
      transition={{ delay }}
      whileHover={{ scale: 1.01, x: 3 }}
      style={styles.settingRow}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
        <Icon size={18} color="#9d96c8" />
        <span style={styles.settingLabel}>{label}</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <span style={styles.settingValue}>{value}</span>
        <ChevronRight size={16} color="#5a5480" />
      </div>
    </motion.div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  pageHdr: { marginBottom: "2rem" },
  pageTitle: {
    fontFamily: "'Syne', sans-serif",
    fontSize: 26,
    fontWeight: 800,
    color: "#ede9ff",
    letterSpacing: "-0.5px",
    marginBottom: 4,
  },
  pageSub: { fontSize: 13, color: "#5a5480" },
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
    marginBottom: "1.5rem",
  },
  walletIcon: {
    width: 56,
    height: 56,
    background: "linear-gradient(135deg, #4c26c8, #7c3aed)",
    borderRadius: 16,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    boxShadow: "0 10px 30px rgba(124,58,237,0.3)",
  },
  cardTitle: {
    fontFamily: "'Syne', sans-serif",
    fontWeight: 600,
    fontSize: "1.125rem",
    color: "#ede9ff",
  },
  cardSubtext: { color: "#9d96c8", fontSize: "0.875rem" },
  statusBadge: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    padding: "0.375rem 0.75rem",
    background: "rgba(16,185,129,0.1)",
    border: "1px solid rgba(16,185,129,0.2)",
    borderRadius: 100,
    fontSize: "0.75rem",
    fontWeight: 600,
    color: "#34d399",
  },
  statusDot: {
    width: 6,
    height: 6,
    background: "#10b981",
    borderRadius: "50%",
    boxShadow: "0 0 6px #10b981",
  },
  addressBox: {
    background: "rgba(255,255,255,0.03)",
    borderRadius: 12,
    padding: "1rem",
    marginBottom: "1rem",
  },
  addressLabel: {
    fontSize: "0.75rem",
    color: "#5a5480",
    marginBottom: "0.5rem",
  },
  addressCode: {
    flex: 1,
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: "0.85rem",
    color: "#9d96c8",
    wordBreak: "break-all",
  },
  copyBtn: {
    padding: "0.5rem",
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 8,
    cursor: "pointer",
  },
  explorerBtn: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    padding: "0.625rem 1rem",
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 10,
    color: "#9d96c8",
    textDecoration: "none",
    fontWeight: 500,
    fontSize: "0.875rem",
  },
  disconnectBtn: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    padding: "0.625rem 1rem",
    background: "rgba(244,63,94,0.1)",
    border: "1px solid rgba(244,63,94,0.2)",
    borderRadius: 10,
    color: "#fb7185",
    fontWeight: 500,
    fontSize: "0.875rem",
    cursor: "pointer",
  },
  sectionHeader: {
    display: "flex",
    alignItems: "center",
    gap: "0.75rem",
    marginBottom: "1.25rem",
  },
  sectionIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  sectionTitle: {
    fontFamily: "'Syne', sans-serif",
    fontWeight: 600,
    fontSize: "1rem",
    color: "#ede9ff",
  },
  sectionDesc: { fontSize: "0.8rem", color: "#5a5480" },
  toggleList: { display: "flex", flexDirection: "column", gap: "0.75rem" },
  toggleRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0.75rem",
    background: "rgba(255,255,255,0.03)",
    borderRadius: 12,
    cursor: "pointer",
    border: "1px solid rgba(255,255,255,0.05)",
  },
  toggleLabel: { fontWeight: 500, color: "#ede9ff", marginBottom: "0.125rem" },
  toggleDesc: { fontSize: "0.8rem", color: "#5a5480" },
  toggleTrack: {
    width: 44,
    height: 24,
    borderRadius: 100,
    position: "relative",
  },
  toggleThumb: {
    position: "absolute",
    top: 2,
    width: 20,
    height: 20,
    background: "white",
    borderRadius: "50%",
    boxShadow: "0 1px 3px rgba(0,0,0,0.3)",
  },
  settingRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0.75rem",
    background: "rgba(255,255,255,0.03)",
    borderRadius: 12,
    cursor: "pointer",
    border: "1px solid rgba(255,255,255,0.05)",
  },
  settingLabel: { fontWeight: 500, color: "#ede9ff" },
  settingValue: { color: "#5a5480", fontSize: "0.9rem" },
};
