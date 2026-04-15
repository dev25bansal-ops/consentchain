import { Component, ReactNode } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("Error caught by boundary:", error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div style={styles.container}>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            style={styles.card}
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.1 }}
              style={styles.icon}
            >
              <AlertTriangle size={32} />
            </motion.div>
            <h2 style={styles.title}>Something went wrong</h2>
            <p style={styles.message}>
              {this.state.error?.message || "An unexpected error occurred"}
            </p>
            <motion.button
              onClick={this.handleRetry}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              style={styles.button}
            >
              <RefreshCw size={16} />
              Try Again
            </motion.button>
          </motion.div>
        </div>
      );
    }

    return this.props.children;
  }
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "100vh",
    padding: 20,
    background: "#0b0917",
  },
  card: {
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 20,
    padding: "48px 40px",
    textAlign: "center",
    maxWidth: 400,
  },
  icon: {
    width: 64,
    height: 64,
    borderRadius: 16,
    background: "rgba(244,63,94,0.1)",
    border: "1px solid rgba(244,63,94,0.2)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    margin: "0 auto 24px",
    color: "#fb7185",
  },
  title: {
    fontFamily: "'Syne', sans-serif",
    fontSize: 22,
    fontWeight: 700,
    color: "#ede9ff",
    marginBottom: 8,
  },
  message: {
    fontSize: 14,
    color: "#5a5480",
    marginBottom: 24,
    lineHeight: 1.6,
  },
  button: {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    padding: "12px 24px",
    background: "linear-gradient(135deg, #7c3aed, #9333ea)",
    border: "none",
    borderRadius: 10,
    color: "white",
    fontWeight: 600,
    fontSize: 14,
    cursor: "pointer",
  },
};
