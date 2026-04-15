import {
  createContext,
  useContext,
  useState,
  useCallback,
  ReactNode,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from "lucide-react";

type ToastType = "success" | "error" | "warning" | "info";

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

interface ToastContextType {
  toasts: Toast[];
  addToast: (
    type: ToastType,
    title: string,
    message?: string,
    duration?: number,
  ) => void;
  removeToast: (id: string) => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (type: ToastType, title: string, message?: string, duration = 5000) => {
      const id = `toast_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const toast: Toast = { id, type, title, message, duration };
      setToasts((prev) => [...prev, toast]);

      if (duration > 0) {
        setTimeout(() => removeToast(id), duration);
      }
    },
    [removeToast],
  );

  const success = useCallback(
    (title: string, message?: string) => addToast("success", title, message),
    [addToast],
  );

  const error = useCallback(
    (title: string, message?: string) => addToast("error", title, message),
    [addToast],
  );

  const warning = useCallback(
    (title: string, message?: string) => addToast("warning", title, message),
    [addToast],
  );

  const info = useCallback(
    (title: string, message?: string) => addToast("info", title, message),
    [addToast],
  );

  return (
    <ToastContext.Provider
      value={{ toasts, addToast, removeToast, success, error, warning, info }}
    >
      {children}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </ToastContext.Provider>
  );
}

function ToastContainer({
  toasts,
  removeToast,
}: {
  toasts: Toast[];
  removeToast: (id: string) => void;
}) {
  return (
    <div style={styles.container}>
      <AnimatePresence>
        {toasts.map((toast) => (
          <ToastItem
            key={toast.id}
            toast={toast}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}

function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  const config = {
    success: {
      icon: CheckCircle,
      color: "#10b981",
      bg: "rgba(16,185,129,0.1)",
      border: "rgba(16,185,129,0.2)",
    },
    error: {
      icon: AlertCircle,
      color: "#f43f5e",
      bg: "rgba(244,63,94,0.1)",
      border: "rgba(244,63,94,0.2)",
    },
    warning: {
      icon: AlertTriangle,
      color: "#f59e0b",
      bg: "rgba(245,158,11,0.1)",
      border: "rgba(245,158,11,0.2)",
    },
    info: {
      icon: Info,
      color: "#3b82f6",
      bg: "rgba(59,130,246,0.1)",
      border: "rgba(59,130,246,0.2)",
    },
  };

  const { icon: Icon, color, bg, border } = config[toast.type];

  return (
    <motion.div
      initial={{ opacity: 0, x: 300, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 300, scale: 0.95 }}
      transition={{ type: "spring", damping: 25, stiffness: 300 }}
      style={{ ...styles.toast, background: bg, border: `1px solid ${border}` }}
    >
      <div style={{ ...styles.iconWrap, color }}>
        <Icon size={20} />
      </div>
      <div style={styles.content}>
        <div style={{ ...styles.title, color }}>{toast.title}</div>
        {toast.message && <div style={styles.message}>{toast.message}</div>}
      </div>
      <motion.button
        onClick={onClose}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        style={styles.closeBtn}
      >
        <X size={14} />
      </motion.button>
    </motion.div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: "fixed",
    top: 20,
    right: 20,
    zIndex: 9999,
    display: "flex",
    flexDirection: "column",
    gap: 8,
    maxWidth: 380,
  },
  toast: {
    display: "flex",
    alignItems: "flex-start",
    gap: 12,
    padding: "14px 16px",
    borderRadius: 12,
    backdropFilter: "blur(12px)",
    boxShadow: "0 10px 40px rgba(0,0,0,0.3)",
  },
  iconWrap: {
    flexShrink: 0,
    marginTop: 1,
  },
  content: {
    flex: 1,
    minWidth: 0,
  },
  title: {
    fontWeight: 600,
    fontSize: 14,
    marginBottom: 2,
  },
  message: {
    fontSize: 12,
    color: "#9d96c8",
    lineHeight: 1.4,
  },
  closeBtn: {
    flexShrink: 0,
    padding: 4,
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 6,
    color: "#5a5480",
    cursor: "pointer",
  },
};
