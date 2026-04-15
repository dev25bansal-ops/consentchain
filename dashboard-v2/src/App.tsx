import { Routes, Route, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { lazy, Suspense } from "react";
import Layout from "./components/Layout";
import { Loader2 } from "lucide-react";

// Lazy-loaded page components for route-based code splitting
const Dashboard = lazy(() => import("./pages/Dashboard"));
const ConsentDetail = lazy(() => import("./pages/ConsentDetail"));
const Settings = lazy(() => import("./pages/Settings"));
const Grievances = lazy(() => import("./pages/Grievances"));
const Fiduciaries = lazy(() => import("./pages/Fiduciaries"));
const History = lazy(() => import("./pages/History"));
const Activity = lazy(() => import("./pages/Activity"));
const Profile = lazy(() => import("./pages/Profile"));
import { useWallet } from "./hooks/useWallet";
import { WalletId } from "@txnlab/use-wallet";
import {
  staggerContainer,
  staggerItem,
  scaleInCenter,
  pageTransition,
} from "./lib/animations";

function LoadingSpinner() {
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

function App() {
  const { isConnected } = useWallet();
  const location = useLocation();

  if (!isConnected) {
    return <LandingPage />;
  }

  return (
    <Layout>
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route
            path="/"
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <AnimatedPage>
                  <Dashboard />
                </AnimatedPage>
              </Suspense>
            }
          />
          <Route
            path="/consent/:id"
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <AnimatedPage>
                  <ConsentDetail />
                </AnimatedPage>
              </Suspense>
            }
          />
          <Route
            path="/settings"
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <AnimatedPage>
                  <Settings />
                </AnimatedPage>
              </Suspense>
            }
          />
          <Route
            path="/grievances"
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <AnimatedPage>
                  <Grievances />
                </AnimatedPage>
              </Suspense>
            }
          />
          <Route
            path="/fiduciaries"
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <AnimatedPage>
                  <Fiduciaries />
                </AnimatedPage>
              </Suspense>
            }
          />
          <Route
            path="/data-fiduciaries"
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <AnimatedPage>
                  <Fiduciaries />
                </AnimatedPage>
              </Suspense>
            }
          />
          <Route
            path="/history"
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <AnimatedPage>
                  <History />
                </AnimatedPage>
              </Suspense>
            }
          />
          <Route
            path="/activity"
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <AnimatedPage>
                  <Activity />
                </AnimatedPage>
              </Suspense>
            }
          />
          <Route
            path="/profile"
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <AnimatedPage>
                  <Profile />
                </AnimatedPage>
              </Suspense>
            }
          />
        </Routes>
      </AnimatePresence>
    </Layout>
  );
}

function AnimatedPage({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      variants={pageTransition}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ duration: 0.2 }}
    >
      {children}
    </motion.div>
  );
}

function LandingPage() {
  return (
    <div style={styles.page}>
      <div style={styles.bgCanvas} />

      <motion.div
        style={styles.orb1}
        animate={{
          x: [0, 30, -20, 0],
          y: [0, -40, 20, 0],
          scale: [1, 1.05, 0.95, 1],
        }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        style={styles.orb2}
        animate={{
          x: [0, -20, 30, 0],
          y: [0, 40, -20, 0],
          scale: [1, 0.95, 1.05, 1],
        }}
        transition={{
          duration: 28,
          repeat: Infinity,
          ease: "easeInOut",
          delay: -10,
        }}
      />
      <motion.div
        style={styles.orb3}
        animate={{
          x: [0, 20, -30, 0],
          y: [0, -30, 40, 0],
          scale: [1, 1.08, 0.92, 1],
        }}
        transition={{
          duration: 18,
          repeat: Infinity,
          ease: "easeInOut",
          delay: -5,
        }}
      />

      <div style={styles.grain} />

      <Particles />

      <motion.div
        variants={scaleInCenter}
        initial="initial"
        animate="animate"
        style={styles.cardWrap}
      >
        <div style={styles.card}>
          <motion.div
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            style={styles.header}
          >
            <div style={styles.logoRing}>
              <motion.div
                style={styles.logoRingGradient}
                animate={{ rotate: 360 }}
                transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
              />
              <div style={styles.logoRingBg} />
              <motion.div
                style={styles.logoIcon}
                whileHover={{ scale: 1.05, rotate: [0, -5, 5, 0] }}
              >
                <ShieldIcon />
              </motion.div>
            </div>

            <motion.h1 variants={staggerItem} style={styles.brandName}>
              ConsentChain
            </motion.h1>

            <motion.p variants={staggerItem} style={styles.subtitle}>
              DPDP Act Compliant Consent Management
              <br />
              on Algorand
            </motion.p>
          </motion.div>

          <motion.div
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            style={styles.badges}
          >
            <Badge icon="🔒" label="Secure" color="#10b981" />
            <Badge icon="⚡" label="4.5s Finality" color="#f59e0b" />
            <Badge icon="✓" label="DPDP Compliant" color="#22d3ee" />
          </motion.div>

          <motion.div variants={staggerItem} style={styles.networkPill}>
            <motion.div
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              style={{
                ...styles.netDot,
                background: "#10b981",
                boxShadow: "0 0 8px #10b981",
              }}
            />
            Algorand Testnet · 0.001 ALGO / tx
          </motion.div>

          <ConnectWalletSection />

          <div style={styles.divider} />

          <motion.p variants={staggerItem} style={styles.footerNote}>
            By connecting, you agree to manage your data consents on-chain
            <br />
            under{" "}
            <a href="#" style={styles.footerLink}>
              DPDP Act 2023
            </a>{" "}
            ·{" "}
            <a href="#" style={styles.footerLink}>
              Privacy Policy
            </a>
          </motion.p>

          <motion.div variants={staggerItem} style={styles.powered}>
            <svg width="14" height="14" viewBox="0 0 32 32" fill="none">
              <circle cx="16" cy="16" r="14" fill="#00b4ab" />
              <circle cx="16" cy="16" r="6" fill="white" />
            </svg>
            Secured by{" "}
            <span style={styles.poweredSpan}>Algorand Blockchain</span>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}

function Particles() {
  const particles = Array.from({ length: 28 }, (_, i) => ({
    id: i,
    left: Math.random() * 100,
    size: Math.random() * 3 + 1,
    duration: Math.random() * 12 + 8,
    delay: Math.random() * -20,
    dx: (Math.random() - 0.5) * 60,
    opacity: Math.random() * 0.5 + 0.2,
  }));

  return (
    <div style={styles.particles}>
      {particles.map((p) => (
        <motion.div
          key={p.id}
          style={{
            ...styles.particle,
            left: `${p.left}%`,
            width: p.size,
            height: p.size,
          }}
          animate={{
            y: [100, -10],
            x: [0, p.dx],
            opacity: [0, p.opacity, p.opacity * 0.8, 0],
          }}
          transition={{
            duration: p.duration,
            repeat: Infinity,
            delay: p.delay,
            ease: "linear",
          }}
        />
      ))}
    </div>
  );
}

function Badge({
  label,
  color,
}: {
  icon: string;
  label: string;
  color: string;
}) {
  return (
    <motion.div
      variants={staggerItem}
      whileHover={{ scale: 1.05, y: -2 }}
      style={styles.badge}
    >
      <motion.div
        animate={{ scale: [1, 1.2, 1], opacity: [1, 0.5, 1] }}
        transition={{ duration: 2, repeat: Infinity }}
        style={{
          ...styles.badgeDot,
          background: color,
          boxShadow: `0 0 6px ${color}`,
        }}
      />
      {label}
    </motion.div>
  );
}

function ShieldIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
      <path
        d="M16 4L26 9V16C26 21.5 21.5 26.5 16 28C10.5 26.5 6 21.5 6 16V9L16 4Z"
        fill="rgba(255,255,255,0.12)"
        stroke="rgba(255,255,255,0.4)"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M11.5 16L14.5 19L20.5 13"
        stroke="white"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ConnectWalletSection() {
  const { connect, loading } = useWallet();

  const wallets = [
    {
      id: WalletId.PERA,
      name: "Pera Wallet",
      icon: "🦊",
      primary: true,
      meta: "Mobile & Desktop · WalletConnect",
    },
    {
      id: WalletId.EXODUS,
      name: "Exodus Wallet",
      icon: "💎",
      primary: false,
      meta: "Desktop · Browser Extension",
    },
    {
      id: WalletId.DEFLY,
      name: "Defly Wallet",
      icon: "🚀",
      primary: false,
      meta: "Mobile · DeFi Optimized",
    },
  ];

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      style={styles.wallets}
    >
      {wallets.map((wallet) => (
        <motion.button
          key={wallet.id}
          variants={staggerItem}
          onClick={() => connect(wallet.id)}
          disabled={loading}
          whileHover={{ y: -2 }}
          whileTap={{ scale: 0.98 }}
          style={{
            ...styles.walletBtn,
            ...(wallet.primary ? styles.walletBtnPrimary : {}),
          }}
        >
          <div style={styles.walletIcon}>{wallet.icon}</div>
          <div style={{ flex: 1, textAlign: "left" }}>
            {wallet.primary && <span style={styles.tagRec}>★ Recommended</span>}
            <div style={styles.walletLabel}>Connect {wallet.name}</div>
            <div style={styles.walletMeta}>{wallet.meta}</div>
          </div>
          {loading ? (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 0.7, repeat: Infinity, ease: "linear" }}
              style={styles.spinner}
            />
          ) : (
            <motion.div whileHover={{ x: 3 }} style={styles.walletArrow}>
              <svg
                width="14"
                height="14"
                viewBox="0 0 14 14"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M3 7h8M7 3l4 4-4 4" />
              </svg>
            </motion.div>
          )}
        </motion.button>
      ))}
    </motion.div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  loadingContainer: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "60vh",
  },
  page: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "#0d0b1a",
    position: "relative",
    overflow: "hidden",
    color: "#f1f0ff",
    fontFamily:
      "'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },
  bgCanvas: {
    position: "fixed",
    inset: 0,
    zIndex: 0,
    background: `
      radial-gradient(ellipse 80% 60% at 20% 30%, #1e0b4a 0%, transparent 60%),
      radial-gradient(ellipse 60% 50% at 80% 70%, #0b1640 0%, transparent 60%),
      radial-gradient(ellipse 40% 40% at 50% 50%, #110928 0%, transparent 70%),
      #0d0b1a
    `,
  },
  orb1: {
    position: "fixed",
    width: 400,
    height: 400,
    background:
      "radial-gradient(circle, rgba(108,61,232,0.35), transparent 70%)",
    borderRadius: "50%",
    filter: "blur(80px)",
    top: "-10%",
    left: "-5%",
    pointerEvents: "none",
  },
  orb2: {
    position: "fixed",
    width: 300,
    height: 300,
    background:
      "radial-gradient(circle, rgba(34,211,238,0.2), transparent 70%)",
    borderRadius: "50%",
    filter: "blur(80px)",
    bottom: "5%",
    right: "5%",
    pointerEvents: "none",
  },
  orb3: {
    position: "fixed",
    width: 200,
    height: 200,
    background: "radial-gradient(circle, rgba(79,70,229,0.3), transparent 70%)",
    borderRadius: "50%",
    filter: "blur(80px)",
    top: "40%",
    right: "15%",
    pointerEvents: "none",
  },
  grain: {
    position: "fixed",
    inset: 0,
    zIndex: 1,
    pointerEvents: "none",
    opacity: 0.025,
    backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
    backgroundSize: 180,
  },
  particles: {
    position: "fixed",
    inset: 0,
    zIndex: 1,
    pointerEvents: "none",
  },
  particle: {
    position: "absolute",
    background: "rgba(139,92,246,0.6)",
    borderRadius: "50%",
  },
  cardWrap: {
    position: "relative",
    zIndex: 10,
    width: 420,
  },
  card: {
    background: "rgba(18,12,38,0.85)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 28,
    padding: "44px 40px 36px",
    backdropFilter: "blur(32px) saturate(160%)",
    boxShadow: `
      0 0 0 1px rgba(139,92,246,0.12),
      0 40px 80px rgba(0,0,0,0.6),
      0 0 60px rgba(108,61,232,0.08),
      inset 0 1px 0 rgba(255,255,255,0.07)
    `,
    position: "relative",
    overflow: "hidden",
  },
  header: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 20,
    marginBottom: 32,
    position: "relative",
    zIndex: 1,
  },
  logoRing: {
    position: "relative",
    width: 72,
    height: 72,
  },
  logoRingGradient: {
    position: "absolute",
    inset: -4,
    borderRadius: 26,
    background: "conic-gradient(from 0deg, #6c3de8, #22d3ee, #4f46e5, #6c3de8)",
    opacity: 0.7,
  },
  logoRingBg: {
    position: "absolute",
    inset: -2,
    borderRadius: 24,
    background: "#0d0b1a",
  },
  logoIcon: {
    position: "relative",
    zIndex: 1,
    width: 72,
    height: 72,
    background: "linear-gradient(135deg, #4c26c8, #6c3de8, #8b5cf6)",
    borderRadius: 22,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    boxShadow:
      "0 8px 32px rgba(108,61,232,0.4), inset 0 1px 0 rgba(255,255,255,0.15)",
  },
  brandName: {
    fontSize: 28,
    fontWeight: 800,
    fontFamily: "'Syne', sans-serif",
    letterSpacing: "-0.5px",
    background:
      "linear-gradient(135deg, #e8e0ff 0%, #b794f4 50%, #7c3aed 100%)",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
    backgroundClip: "text",
  },
  subtitle: {
    fontSize: 13,
    fontWeight: 300,
    color: "#a49ecf",
    textAlign: "center",
    lineHeight: 1.5,
    letterSpacing: "0.01em",
  },
  badges: {
    display: "flex",
    gap: 8,
    justifyContent: "center",
    flexWrap: "wrap",
    marginBottom: 32,
    position: "relative",
    zIndex: 1,
  },
  badge: {
    display: "flex",
    alignItems: "center",
    gap: 5,
    padding: "5px 12px",
    borderRadius: 100,
    fontSize: 11,
    fontWeight: 500,
    letterSpacing: "0.03em",
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.04)",
    color: "#a49ecf",
    cursor: "default",
  },
  badgeDot: {
    width: 6,
    height: 6,
    borderRadius: "50%",
  },
  networkPill: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "8px 14px",
    background: "rgba(16,185,129,0.06)",
    border: "1px solid rgba(16,185,129,0.2)",
    borderRadius: 100,
    fontSize: 12,
    color: "#6ee7b7",
    marginBottom: 28,
    width: "fit-content",
    marginLeft: "auto",
    marginRight: "auto",
    position: "relative",
    zIndex: 1,
  },
  netDot: {
    width: 7,
    height: 7,
    borderRadius: "50%",
  },
  wallets: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
    marginBottom: 24,
    position: "relative",
    zIndex: 1,
  },
  walletBtn: {
    position: "relative",
    overflow: "hidden",
    display: "flex",
    alignItems: "center",
    width: "100%",
    padding: "15px 20px",
    borderRadius: 20,
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.04)",
    cursor: "pointer",
    outline: "none",
    color: "#f1f0ff",
  },
  walletBtnPrimary: {
    background: "linear-gradient(135deg, #4c26c8, #6c3de8 50%, #7c3aed)",
    borderColor: "rgba(139,92,246,0.5)",
    boxShadow:
      "0 4px 20px rgba(108,61,232,0.35), inset 0 1px 0 rgba(255,255,255,0.15)",
  },
  walletIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 20,
    flexShrink: 0,
    marginRight: 14,
    background: "rgba(255,255,255,0.07)",
    border: "1px solid rgba(255,255,255,0.08)",
  },
  tagRec: {
    fontSize: 9,
    letterSpacing: "0.06em",
    fontWeight: 600,
    textTransform: "uppercase",
    background: "linear-gradient(90deg, #f59e0b, #fb923c)",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
    backgroundClip: "text",
    marginBottom: 2,
    display: "block",
  },
  walletLabel: {
    fontSize: 14.5,
    fontWeight: 600,
    fontFamily: "'Syne', sans-serif",
    letterSpacing: "0.01em",
    color: "#f1f0ff",
  },
  walletMeta: {
    fontSize: 10,
    fontWeight: 400,
    color: "#6b6690",
    marginTop: 1,
    letterSpacing: "0.02em",
  },
  walletArrow: {
    width: 28,
    height: 28,
    borderRadius: 8,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "rgba(255,255,255,0.05)",
    border: "1px solid rgba(255,255,255,0.07)",
    flexShrink: 0,
    color: "#6b6690",
  },
  spinner: {
    width: 18,
    height: 18,
    borderRadius: "50%",
    border: "2px solid rgba(255,255,255,0.15)",
    borderTopColor: "#8b5cf6",
    flexShrink: 0,
  },
  divider: {
    height: 1,
    background:
      "linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent)",
    marginBottom: 20,
    position: "relative",
    zIndex: 1,
  },
  footerNote: {
    textAlign: "center",
    fontSize: 11,
    color: "#6b6690",
    lineHeight: 1.6,
    position: "relative",
    zIndex: 1,
  },
  footerLink: {
    color: "#a49ecf",
    textDecoration: "none",
    borderBottom: "1px solid rgba(164,158,207,0.2)",
  },
  powered: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    fontSize: 10.5,
    color: "#6b6690",
    letterSpacing: "0.03em",
    marginTop: 16,
    position: "relative",
    zIndex: 1,
  },
  poweredSpan: {
    color: "#a49ecf",
    fontWeight: 500,
  },
};

export default App;
