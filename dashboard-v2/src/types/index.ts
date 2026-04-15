// Type definitions for the ConsentChain Dashboard application

// ==================== Wallet Types ====================
export type WalletProvider = "pera" | "exodus" | "defly";

export interface WalletAccount {
  address: string;
  name?: string;
}

export interface WalletState {
  isConnected: boolean;
  address: string | null;
  accounts: WalletAccount[];
  activeAccount: WalletAccount | null;
  isLoading: boolean;
  error: string | null;
}

// ==================== Consent Types ====================
export type ConsentStatus =
  | "GRANTED"
  | "REVOKED"
  | "EXPIRED"
  | "PENDING"
  | "MODIFIED";

export type ConsentPurpose =
  | "MARKETING"
  | "ANALYTICS"
  | "SERVICE_DELIVERY"
  | "RESEARCH"
  | "PERSONALIZATION"
  | "THIRD_PARTY_SHARING";

export type DataType =
  | "PERSONAL_INFO"
  | "CONTACT_INFO"
  | "FINANCIAL_DATA"
  | "HEALTH_DATA"
  | "BIOMETRIC_DATA"
  | "LOCATION_DATA"
  | "BEHAVIORAL_DATA"
  | "SENSITIVE_DATA";

export interface Consent {
  consent_id: string;
  principal_id: string;
  fiduciary_id: string;
  purpose: ConsentPurpose;
  data_types: DataType[];
  status: ConsentStatus;
  granted_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  consent_hash: string;
  on_chain_tx_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConsentEvent {
  event_id: string;
  consent_id: string;
  event_type: string;
  actor: string;
  previous_status: ConsentStatus | null;
  new_status: ConsentStatus;
  created_at: string;
  tx_id: string | null;
}

// ==================== API Response Types ====================
export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  limit: number;
  total: number;
  has_more: boolean;
}

export interface ConsentQueryParams {
  principal_id?: string;
  principal_wallet?: string;
  fiduciary_id?: string;
  status?: ConsentStatus;
  purpose?: ConsentPurpose;
  from_date?: string;
  to_date?: string;
  page?: number;
  limit?: number;
}

export interface ConsentCreateRequest {
  principal_wallet: string;
  fiduciary_id: string;
  purpose: ConsentPurpose;
  data_types: DataType[];
  duration_days: number;
  metadata?: Record<string, unknown>;
  signature: string;
}

export interface ConsentRevokeRequest {
  consent_id: string;
  reason?: string;
  signature: string;
}

// ==================== Dashboard Types ====================
export interface DashboardStats {
  activeConsents: number;
  revokedConsents: number;
  expiringSoon: number;
  totalFiduciaries: number;
  consentTrend: number;
}

export interface DashboardFilters {
  status: ConsentStatus | "";
  purpose: ConsentPurpose | "";
  search: string;
}

// ==================== Settings Types ====================
export interface NotificationSettings {
  expiryReminders: boolean;
  revokeNotifications: boolean;
  securityAlerts: boolean;
  marketing: boolean;
}

export interface PrivacySettings {
  ipfsStorage: boolean;
  onChainVerification: boolean;
  dataSharing: boolean;
}

export interface UserSettings {
  notifications: NotificationSettings;
  privacy: PrivacySettings;
  language: "en" | "hi" | "ta" | "te" | "bn";
  theme: "light" | "dark" | "system";
}

// ==================== UI Component Types ====================
export interface ButtonProps {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
  disabled?: boolean;
  fullWidth?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  children: React.ReactNode;
  onClick?: () => void;
  type?: "button" | "submit" | "reset";
  className?: string;
  "aria-label"?: string;
}

export interface CardProps {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  onClick?: () => void;
  interactive?: boolean;
  padding?: "none" | "sm" | "md" | "lg";
  shadow?: "none" | "sm" | "md" | "lg";
}

export interface BadgeProps {
  status: ConsentStatus;
  size?: "sm" | "md";
}

export interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ComponentType<{
    className?: string;
    style?: React.CSSProperties;
  }>;
  trend?: string;
  trendDirection?: "up" | "down" | "neutral";
  color: "primary" | "success" | "warning" | "error" | "info";
  delay?: number;
}

export interface ToggleSwitchProps {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export interface InputProps {
  type?: "text" | "email" | "password" | "search" | "number";
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  label?: string;
  id?: string;
  name?: string;
  required?: boolean;
}

export interface SelectProps {
  options: Array<{ value: string; label: string }>;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  label?: string;
  id?: string;
  name?: string;
  error?: string;
}

// ==================== Error Types ====================
export class AppError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode?: number,
    public details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "AppError";
  }
}

export interface ErrorState {
  hasError: boolean;
  message: string;
  code?: string;
}

// ==================== Utility Types ====================
export type AsyncState<T> = {
  data: T | null;
  isLoading: boolean;
  error: ErrorState | null;
};

export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type RequiredKeys<T> = {
  [K in keyof T]-?: {} extends Pick<T, K> ? never : K;
}[keyof T];

export type OptionalKeys<T> = {
  [K in keyof T]-?: {} extends Pick<T, K> ? K : never;
}[keyof T];
