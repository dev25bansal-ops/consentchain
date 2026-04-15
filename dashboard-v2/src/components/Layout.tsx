import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useWallet } from "../hooks/useWallet";
import {
  Shield,
  Clock,
  Building2,
  Activity,
  Users,
  User,
  Settings,
  Bell,
  LogOut,
  Search,
  AlertTriangle,
} from "lucide-react";

const navItems = [
  {
    section: "Manage",
    items: [
      { label: "My Consents", path: "/", icon: Shield, badge: 4 },
      { label: "Consent History", path: "/history", icon: Clock },
      { label: "Fiduciaries", path: "/fiduciaries", icon: Building2 },
    ],
  },
  {
    section: "Analytics",
    items: [
      { label: "On-Chain Activity", path: "/activity", icon: Activity },
      { label: "Data Fiduciaries", path: "/data-fiduciaries", icon: Users },
    ],
  },
  {
    section: "Support",
    items: [{ label: "Grievances", path: "/grievances", icon: AlertTriangle }],
  },
  {
    section: "Account",
    items: [
      { label: "Profile", path: "/profile", icon: User },
      { label: "Settings", path: "/settings", icon: Settings },
    ],
  },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { address, disconnect } = useWallet();
  const [notifOpen, setNotifOpen] = useState(false);
  const [searchFocused, setSearchFocused] = useState(false);

  const shortAddress = address
    ? `${address.slice(0, 6)}…${address.slice(-4)}`
    : "";

  return (
    <div style={styles.page}>
      <aside style={styles.sidebar}>
        <div style={styles.sidebarLogo}>
          <motion.div
            style={styles.logoBox}
            whileHover={{ scale: 1.05, rotate: [0, -5, 5, 0] }}
          >
            <svg viewBox="0 0 32 32" fill="none" width={18} height={18}>
              <path
                d="M16 4L26 9V16C26 21.5 21.5 26.5 16 28C10.5 26.5 6 21.5 6 16V9L16 4Z"
                fill="rgba(255,255,255,0.15)"
                stroke="rgba(255,255,255,0.5)"
                strokeWidth="1.5"
              />
              <path
                d="M11.5 16L14.5 19L20.5 13"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </motion.div>
          <span style={styles.brand}>ConsentChain</span>
        </div>

        {navItems.map((section, i) => (
          <div key={i} style={styles.navSection}>
            <div style={styles.navLabel}>{section.section}</div>
            {section.items.map((item) => {
              const isActive = location.pathname === item.path;
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  style={{
                    ...styles.navItem,
                    ...(isActive ? styles.navItemActive : {}),
                  }}
                >
                  {isActive && <div style={styles.navItemIndicator} />}
                  <Icon size={16} />
                  <span>{item.label}</span>
                  {item.badge && (
                    <span style={styles.navBadge}>{item.badge}</span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}

        <div style={styles.sidebarBottom}>
          <div style={styles.walletPill}>
            <div style={styles.walletNet}>
              <motion.div
                animate={{ scale: [1, 1.2, 1], opacity: [1, 0.4, 1] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                style={styles.walletDot}
              />
              Algorand Testnet
            </div>
            <div style={styles.walletAddr}>{shortAddress}</div>
          </div>
        </div>
      </aside>

      <div style={styles.main}>
        <header style={styles.topbar}>
          <div
            style={{
              ...styles.topbarSearch,
              ...(searchFocused ? styles.topbarSearchFocused : {}),
            }}
          >
            <Search size={14} color="#5a5480" />
            <input
              type="text"
              placeholder="Search consents, fiduciaries..."
              style={styles.searchInput}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setSearchFocused(false)}
            />
          </div>

          <div style={styles.topbarRight}>
            <motion.div
              style={styles.iconBtn}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setNotifOpen(!notifOpen)}
            >
              <Bell size={16} />
              <div style={styles.notifDot} />
            </motion.div>

            <motion.div
              style={styles.iconBtn}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <User size={16} />
            </motion.div>

            <motion.button
              style={styles.disconnectBtn}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={disconnect}
            >
              <LogOut size={14} />
              Disconnect
            </motion.button>
          </div>

          <AnimatePresence>
            {notifOpen && (
              <motion.div
                initial={{ opacity: 0, y: -8, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.97 }}
                style={styles.notifPanel}
              >
                <div style={styles.notifHdr}>
                  <span style={styles.notifHdrTitle}>Notifications</span>
                  <span style={styles.notifMark}>Mark all read</span>
                </div>
                <div style={styles.notifItem}>
                  <div
                    style={{
                      ...styles.notifIco,
                      background: "rgba(16,185,129,0.1)",
                    }}
                  >
                    ✅
                  </div>
                  <div style={styles.notifBody}>
                    <div style={styles.notifMsg}>
                      Consent granted to <strong>HDFC Bank</strong> confirmed
                      on-chain
                    </div>
                    <div style={styles.notifTime}>
                      2 mins ago · Block #47291834
                    </div>
                  </div>
                </div>
                <div style={styles.notifItem}>
                  <div
                    style={{
                      ...styles.notifIco,
                      background: "rgba(244,63,94,0.1)",
                    }}
                  >
                    ⚠️
                  </div>
                  <div style={styles.notifBody}>
                    <div style={styles.notifMsg}>
                      <strong>Ola Financial</strong> consent expires in 3 days
                    </div>
                    <div style={styles.notifTime}>1 hour ago</div>
                  </div>
                </div>
                <div style={{ ...styles.notifItem, borderBottom: "none" }}>
                  <div
                    style={{
                      ...styles.notifIco,
                      background: "rgba(59,130,246,0.1)",
                    }}
                  >
                    🔗
                  </div>
                  <div style={styles.notifBody}>
                    <div style={styles.notifMsg}>
                      New data fiduciary request from <strong>Zepto</strong>
                    </div>
                    <div style={styles.notifTime}>Yesterday</div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </header>

        <main style={styles.content}>{children}</main>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh",
    display: "flex",
    background: "#0b0917",
    fontFamily: "'DM Sans', sans-serif",
    color: "#ede9ff",
  },
  sidebar: {
    width: 220,
    minHeight: "100vh",
    background: "rgba(15,12,32,0.95)",
    borderRight: "1px solid rgba(255,255,255,0.07)",
    display: "flex",
    flexDirection: "column",
    padding: "24px 0",
    position: "fixed",
    top: 0,
    left: 0,
    zIndex: 100,
    backdropFilter: "blur(20px)",
  },
  sidebarLogo: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "0 20px 24px",
    borderBottom: "1px solid rgba(255,255,255,0.07)",
    marginBottom: 12,
  },
  logoBox: {
    width: 34,
    height: 34,
    borderRadius: 10,
    background: "linear-gradient(135deg, #4c26c8, #7c3aed)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    boxShadow: "0 4px 16px rgba(124,58,237,0.35)",
  },
  brand: {
    fontFamily: "'Syne', sans-serif",
    fontSize: 15,
    fontWeight: 700,
    color: "#ede9ff",
  },
  navSection: {
    padding: "0 12px",
    marginBottom: 4,
  },
  navLabel: {
    fontSize: 10,
    letterSpacing: "0.1em",
    textTransform: "uppercase",
    color: "#5a5480",
    padding: "8px 8px 4px",
    fontWeight: 600,
  },
  navItem: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "9px 12px",
    borderRadius: 10,
    fontSize: 13,
    fontWeight: 500,
    color: "#9d96c8",
    cursor: "pointer",
    marginBottom: 2,
    position: "relative",
    textDecoration: "none",
    transition: "all 0.2s ease",
  },
  navItemActive: {
    background: "rgba(124,58,237,0.15)",
    color: "#a78bfa",
  },
  navItemIndicator: {
    position: "absolute",
    left: -12,
    top: "50%",
    transform: "translateY(-50%)",
    width: 3,
    height: 18,
    background: "#a78bfa",
    borderRadius: "0 3px 3px 0",
  },
  navBadge: {
    marginLeft: "auto",
    background: "rgba(124,58,237,0.15)",
    color: "#a78bfa",
    fontSize: 10,
    fontWeight: 600,
    padding: "1px 6px",
    borderRadius: 100,
  },
  sidebarBottom: {
    marginTop: "auto",
    padding: "16px 12px 0",
    borderTop: "1px solid rgba(255,255,255,0.07)",
  },
  walletPill: {
    background: "rgba(16,185,129,0.06)",
    border: "1px solid rgba(16,185,129,0.18)",
    borderRadius: 12,
    padding: "10px 12px",
    cursor: "pointer",
  },
  walletNet: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    fontSize: 10,
    color: "#6ee7b7",
    marginBottom: 4,
  },
  walletDot: {
    width: 6,
    height: 6,
    borderRadius: "50%",
    background: "#10b981",
    boxShadow: "0 0 6px #10b981",
  },
  walletAddr: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 11,
    color: "#9d96c8",
  },
  main: {
    marginLeft: 220,
    flex: 1,
    display: "flex",
    flexDirection: "column",
    minHeight: "100vh",
  },
  topbar: {
    height: 56,
    borderBottom: "1px solid rgba(255,255,255,0.07)",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0 28px",
    background: "rgba(11,9,23,0.8)",
    backdropFilter: "blur(20px)",
    position: "sticky",
    top: 0,
    zIndex: 50,
  },
  topbarSearch: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 10,
    padding: "8px 14px",
    width: 300,
    transition: "all 0.25s ease",
  },
  topbarSearchFocused: {
    borderColor: "#7c3aed",
    boxShadow: "0 0 0 3px rgba(124,58,237,0.15)",
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
  topbarRight: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  iconBtn: {
    width: 36,
    height: 36,
    borderRadius: 10,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    cursor: "pointer",
    color: "#9d96c8",
    position: "relative",
  },
  notifDot: {
    position: "absolute",
    top: 7,
    right: 7,
    width: 6,
    height: 6,
    borderRadius: "50%",
    background: "#f43f5e",
    boxShadow: "0 0 6px #f43f5e",
    border: "1px solid #0b0917",
  },
  disconnectBtn: {
    display: "flex",
    alignItems: "center",
    gap: 7,
    padding: "7px 14px",
    borderRadius: 10,
    background: "rgba(244,63,94,0.07)",
    border: "1px solid rgba(244,63,94,0.2)",
    fontSize: 12,
    fontWeight: 600,
    color: "#fb7185",
    cursor: "pointer",
    fontFamily: "'DM Sans', sans-serif",
  },
  notifPanel: {
    position: "absolute",
    top: 56,
    right: 16,
    width: 300,
    background: "rgba(15,12,32,0.98)",
    border: "1px solid rgba(255,255,255,0.12)",
    borderRadius: 16,
    padding: 16,
    boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
    zIndex: 200,
  },
  notifHdr: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  notifHdrTitle: {
    fontFamily: "'Syne', sans-serif",
    fontSize: 13,
    fontWeight: 700,
  },
  notifMark: {
    fontSize: 10,
    color: "#a78bfa",
    cursor: "pointer",
  },
  notifItem: {
    display: "flex",
    gap: 10,
    padding: "10px 0",
    borderBottom: "1px solid rgba(255,255,255,0.07)",
  },
  notifIco: {
    width: 32,
    height: 32,
    borderRadius: 9,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 15,
    flexShrink: 0,
  },
  notifBody: {
    flex: 1,
  },
  notifMsg: {
    fontSize: 12,
    color: "#ede9ff",
    lineHeight: 1.4,
    marginBottom: 2,
  },
  notifTime: {
    fontSize: 10,
    color: "#5a5480",
  },
  content: {
    padding: "32px 28px",
    flex: 1,
  },
};
