export interface ConsentRecord {
  id: string;
  principal_id: string;
  fiduciary_id: string;
  purpose: string;
  data_types: string[];
  status: ConsentStatus;
  granted_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  on_chain_tx_id: string | null;
  on_chain_app_id: number | null;
  consent_hash: string;
  created_at: string;
  updated_at: string | null;
}

export type ConsentStatus =
  | "GRANTED"
  | "REVOKED"
  | "MODIFIED"
  | "PENDING"
  | "EXPIRED";

export interface ConsentCreate {
  principal_wallet: string;
  fiduciary_id: string;
  purpose: string;
  data_types: string[];
  expires_at?: string;
  metadata?: Record<string, unknown>;
}

export interface ConsentUpdate {
  purpose?: string;
  data_types?: string[];
  expires_at?: string;
  metadata?: Record<string, unknown>;
}

export interface Fiduciary {
  id: string;
  name: string;
  registration_number: string;
  wallet_address: string;
  contact_email: string;
  data_categories: string[];
  purposes: string[];
  compliance_status: string;
  tier: string;
  created_at: string;
}

export interface DataPrincipal {
  id: string;
  wallet_address: string;
  email_hash: string;
  phone_hash: string | null;
  kyc_verified: boolean;
  preferred_language: string;
  created_at: string;
}

export interface WebhookSubscription {
  id: string;
  fiduciary_id: string;
  callback_url: string;
  events: string[];
  active: boolean;
  created_at: string;
}

export interface WebhookDelivery {
  id: string;
  subscription_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  status: string;
  attempts: number;
  last_attempt_at: string | null;
  last_error: string | null;
  delivered_at: string | null;
}

export interface DashboardStats {
  total_consents: number;
  active_consents: number;
  revoked_consents: number;
  expired_consents: number;
  total_fiduciaries: number;
  total_principals: number;
  consent_rate: number;
  avg_expiry_days: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Grievance {
  id: string;
  principal_id: string;
  fiduciary_id: string;
  type: GrievanceType;
  status: GrievanceStatus;
  description: string;
  resolution: string | null;
  created_at: string;
  resolved_at: string | null;
}

export type GrievanceType =
  | "ACCESS"
  | "CORRECTION"
  | "DELETION"
  | "OBJECTION"
  | "OTHER";
export type GrievanceStatus =
  | "PENDING"
  | "IN_PROGRESS"
  | "RESOLVED"
  | "ESCALATED";

export interface ConsentTemplate {
  id: string;
  name: string;
  language: string;
  purpose: string;
  data_types: string[];
  content: string;
  version: number;
  active: boolean;
  created_at: string;
}

export interface ComplianceReport {
  id: string;
  fiduciary_id: string;
  period_start: string;
  period_end: string;
  total_consents: number;
  active_consents: number;
  revoked_consents: number;
  expired_consents: number;
  compliance_score: number;
  on_chain_hash: string | null;
  created_at: string;
}
