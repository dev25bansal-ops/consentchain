const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  api_key?: string;
}

export interface ConsentRecord {
  id: string;
  principal_id: string;
  fiduciary_id: string;
  purpose: string;
  data_types: string[];
  status: string;
  granted_at: string | null;
  expires_at: string | null;
  consent_hash: string;
  on_chain_tx_id: string | null;
  created_at: string;
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

export interface WebhookSubscription {
  id: string;
  fiduciary_id: string;
  callback_url: string;
  events: string[];
  active: boolean;
  created_at: string;
}

export interface Grievance {
  id: string;
  principal_id: string;
  fiduciary_id: string;
  type: string;
  status: string;
  priority: string;
  subject: string;
  description: string;
  created_at: string;
  expected_resolution_date?: string;
  resolution?: string;
  resolved_at: string | null;
}

export interface DeletionRequest {
  id: string;
  principal_id: string;
  fiduciary_id: string;
  scope: string;
  status: string;
  requested_at: string;
  scheduled_at?: string;
  completed_at?: string;
  reason?: string;
  certificate_url?: string;
}

export interface Guardian {
  id: string;
  guardian_wallet: string;
  guardian_name: string;
  guardian_email: string;
  guardian_type: string;
  principal_id: string;
  principal_name?: string;
  principal_category: string;
  status: string;
  valid_from: string;
  valid_until?: string;
  created_at: string;
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
  total_grievances: number;
  open_grievances: number;
  resolved_grievances: number;
  overdue_grievances: number;
  total_deletions: number;
  pending_deletions: number;
  completed_deletions: number;
  compliance_score: number;
  compliance_trend: "up" | "down" | "stable";
  compliance_trend_value: number;
}

export interface ConsentTimeSeriesPoint {
  date: string;
  granted: number;
  revoked: number;
  expired: number;
}

export interface GrievanceByType {
  type: string;
  count: number;
}

export interface ActivityEvent {
  id: string;
  type: string;
  description: string;
  actor: string;
  timestamp: string;
  resource_type: string;
  resource_id: string;
}

export interface ComplianceReport {
  id: string;
  title: string;
  date_range_start: string;
  date_range_end: string;
  generated_at: string;
  generated_by: string;
  status: string;
  download_url?: string;
  compliance_score: number;
}

export interface ConsentFilterParams {
  status?: string;
  purpose?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }

  const json = await response.json();
  // Unwrap APIResponse envelope { success, message, data }
  return (json.data ?? json) as T;
}

export interface FiduciaryListResponse {
  fiduciaries: Fiduciary[];
  page: number;
  limit: number;
  total: number;
}

export interface ConsentListResponse {
  consents: ConsentRecord[];
  page: number;
  limit: number;
  total: number;
  pages: number;
}

export const api = {
  fiduciaries: {
    list: (params?: { status?: string; page?: number; limit?: number }) => {
      const query = new URLSearchParams(
        params as Record<string, string>,
      ).toString();
      return fetchApi<FiduciaryListResponse>(
        `/api/v1/fiduciaries${query ? `?${query}` : ""}`,
      );
    },
    get: (id: string) => fetchApi<Fiduciary>(`/api/v1/fiduciaries/${id}`),
    create: (data: Partial<Fiduciary>) =>
      fetchApi<Fiduciary>("/api/v1/fiduciaries", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Partial<Fiduciary>) =>
      fetchApi<Fiduciary>(`/api/v1/fiduciaries/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    regenerateApiKey: (id: string) =>
      fetchApi<{ api_key: string }>(
        `/api/v1/fiduciaries/${id}/regenerate-key`,
        {
          method: "POST",
        },
      ),
  },

  consents: {
    list: (params?: { fiduciary_id?: string; status?: string; page?: number; limit?: number }) => {
      const query = new URLSearchParams(
        params as Record<string, string>,
      ).toString();
      return fetchApi<ConsentListResponse>(`/api/v1/consent/query?${query}`);
    },
    get: (id: string) => fetchApi<ConsentRecord>(`/api/v1/consent/${id}`),
    stats: () => fetchApi<DashboardStats>("/api/v1/consents/stats"),
    timeseries: (months?: number) =>
      fetchApi<{ timeseries: ConsentTimeSeriesPoint[] }>(
        `/api/v1/consents/timeseries${months ? `?months=${months}` : ""}`,
      ),
  },

  webhooks: {
    list: (fiduciaryId: string) =>
      fetchApi<WebhookSubscription[]>(
        `/api/v1/fiduciaries/${fiduciaryId}/webhooks`,
      ),
    create: (fiduciaryId: string, data: Partial<WebhookSubscription>) =>
      fetchApi<WebhookSubscription>(
        `/api/v1/fiduciaries/${fiduciaryId}/webhooks`,
        {
          method: "POST",
          body: JSON.stringify(data),
        },
      ),
  },

  grievances: {
    list: (params?: { status?: string }) => {
      const query = params
        ? new URLSearchParams(params as Record<string, string>).toString()
        : "";
      return fetchApi<Grievance[]>(`/api/v1/grievances?${query}`);
    },
    get: (id: string) => fetchApi<Grievance>(`/api/v1/grievances/${id}`),
    resolve: (id: string, resolution: string) =>
      fetchApi<Grievance>(`/api/v1/grievances/${id}/resolve`, {
        method: "POST",
        body: JSON.stringify({ resolution }),
      }),
  },
};
