// Design System Tokens
// Centralized design tokens for consistent styling across the application

export const colors = {
  primary: {
    50: "#eff6ff",
    100: "#dbeafe",
    200: "#bfdbfe",
    300: "#93c5fd",
    400: "#60a5fa",
    500: "#3b82f6",
    600: "#2563eb",
    700: "#1d4ed8",
    800: "#1e40af",
    900: "#1e3a8a",
  },
  success: {
    light: "#d1fae5",
    main: "#10b981",
    dark: "#065f46",
  },
  warning: {
    light: "#fef3c7",
    main: "#f59e0b",
    dark: "#92400e",
  },
  error: {
    light: "#fee2e2",
    main: "#ef4444",
    dark: "#991b1b",
  },
  info: {
    light: "#dbeafe",
    main: "#06b6d4",
    dark: "#155e75",
  },
  neutral: {
    50: "#f9fafb",
    100: "#f3f4f6",
    200: "#e5e7eb",
    300: "#d1d5db",
    400: "#9ca3af",
    500: "#6b7280",
    600: "#4b5563",
    700: "#374151",
    800: "#1f2937",
    900: "#111827",
  },
} as const;

export const shadows = {
  sm: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
  md: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
  lg: "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
  xl: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
  glow: "0 0 20px rgba(59, 130, 246, 0.3)",
} as const;

export const transitions = {
  fast: "150ms cubic-bezier(0.4, 0, 0.2, 1)",
  normal: "250ms cubic-bezier(0.4, 0, 0.2, 1)",
  slow: "350ms cubic-bezier(0.4, 0, 0.2, 1)",
} as const;

export const spacing = {
  xs: "0.25rem",
  sm: "0.5rem",
  md: "1rem",
  lg: "1.5rem",
  xl: "2rem",
  "2xl": "3rem",
} as const;

export const borderRadius = {
  sm: "0.375rem",
  md: "0.5rem",
  lg: "0.75rem",
  xl: "1rem",
  full: "9999px",
} as const;

export const typography = {
  fontFamily:
    "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  fontSize: {
    xs: "0.75rem",
    sm: "0.875rem",
    base: "1rem",
    lg: "1.125rem",
    xl: "1.25rem",
    "2xl": "1.5rem",
    "3xl": "1.875rem",
    "4xl": "2.25rem",
  },
  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
    extrabold: 800,
  },
  lineHeight: {
    tight: 1.25,
    normal: 1.5,
    relaxed: 1.625,
  },
} as const;

// Consent Status Configuration
export const CONSENT_STATUS_CONFIG = {
  GRANTED: {
    label: "Granted",
    color: colors.success.main,
    bgColor: colors.success.light,
    textColor: colors.success.dark,
  },
  REVOKED: {
    label: "Revoked",
    color: colors.error.main,
    bgColor: colors.error.light,
    textColor: colors.error.dark,
  },
  EXPIRED: {
    label: "Expired",
    color: colors.warning.main,
    bgColor: colors.warning.light,
    textColor: colors.warning.dark,
  },
  PENDING: {
    label: "Pending",
    color: colors.info.main,
    bgColor: colors.info.light,
    textColor: colors.info.dark,
  },
  MODIFIED: {
    label: "Modified",
    color: colors.primary[500],
    bgColor: colors.primary[100],
    textColor: colors.primary[700],
  },
} as const;

// Animation keyframes
export const keyframes = {
  fadeIn: `
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  `,
  fadeInScale: `
    from { opacity: 0; transform: scale(0.95); }
    to { opacity: 1; transform: scale(1); }
  `,
  slideInUp: `
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
  `,
  spin: `
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  `,
  pulse: `
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.05); opacity: 0.8; }
  `,
  shimmer: `
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  `,
} as const;
