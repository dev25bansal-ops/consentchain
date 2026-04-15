import fetch from "cross-fetch";
import {
  ConsentRecord,
  ConsentCreate,
  ConsentUpdate,
  Fiduciary,
  DataPrincipal,
  WebhookSubscription,
  DashboardStats,
  WebhookDelivery,
  PaginatedResponse,
  Grievance,
  ConsentTemplate,
  ComplianceReport,
} from "./types";
import {
  ConsentChainError,
  AuthenticationError,
  NotFoundError,
  ValidationError,
  RateLimitError,
} from "./errors";

export interface ClientConfig {
  baseUrl?: string;
  apiKey?: string;
  timeout?: number;
}

export class ConsentChainClient {
  private baseUrl: string;
  private apiKey?: string;
  private timeout: number;

  constructor(config: ClientConfig = {}) {
    this.baseUrl = (config.baseUrl || "http://localhost:8000").replace(
      /\/$/,
      "",
    );
    this.apiKey = config.apiKey;
    this.timeout = config.timeout || 30000;
  }

  private async request<T>(
    method: string,
    path: string,
    options: {
      body?: unknown;
      params?: Record<string, string | number | boolean | undefined>;
    } = {},
  ): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`);

    if (options.params) {
      Object.entries(options.params).forEach(([key, value]) => {
        if (value !== undefined) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (this.apiKey) {
      headers["X-API-Key"] = this.apiKey;
    }

    const response = await fetch(url.toString(), {
      method,
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    if (!response.ok) {
      let errorData: Record<string, unknown> = {};
      try {
        errorData = await response.json();
      } catch {
        errorData = { detail: await response.text() };
      }

      const message = String(errorData.detail || "API Error");

      if (response.status === 401) throw new AuthenticationError(message);
      if (response.status === 404) throw new NotFoundError(message);
      if (response.status === 422)
        throw new ValidationError(message, errorData);
      if (response.status === 429) {
        const retryAfter = response.headers.get("Retry-After");
        throw new RateLimitError(
          message,
          retryAfter ? parseInt(retryAfter) : undefined,
        );
      }

      throw new ConsentChainError(message, response.status, errorData);
    }

    return response.json();
  }

  readonly consents = {
    list: async (params?: {
      fiduciary_id?: string;
      status?: string;
      page?: number;
      page_size?: number;
    }): Promise<PaginatedResponse<ConsentRecord>> => {
      return this.request("GET", "/api/v1/consents", { params });
    },

    get: async (id: string): Promise<ConsentRecord> => {
      return this.request("GET", `/api/v1/consents/${id}`);
    },

    create: async (data: ConsentCreate): Promise<ConsentRecord> => {
      return this.request("POST", "/api/v1/consents", { body: data });
    },

    update: async (id: string, data: ConsentUpdate): Promise<ConsentRecord> => {
      return this.request("PUT", `/api/v1/consents/${id}`, { body: data });
    },

    grant: async (id: string, signature: string): Promise<ConsentRecord> => {
      return this.request("POST", `/api/v1/consents/${id}/grant`, {
        body: { signature },
      });
    },

    revoke: async (id: string, reason?: string): Promise<ConsentRecord> => {
      return this.request("POST", `/api/v1/consents/${id}/revoke`, {
        body: { reason },
      });
    },

    verify: async (
      consentHash: string,
    ): Promise<{ valid: boolean; consent?: ConsentRecord }> => {
      return this.request("GET", `/api/v1/consents/verify/${consentHash}`);
    },
  };

  readonly fiduciaries = {
    list: async (): Promise<Fiduciary[]> => {
      return this.request("GET", "/api/v1/fiduciaries");
    },

    get: async (id: string): Promise<Fiduciary> => {
      return this.request("GET", `/api/v1/fiduciaries/${id}`);
    },

    create: async (data: {
      name: string;
      registration_number: string;
      wallet_address: string;
      contact_email: string;
      data_categories: string[];
      purposes: string[];
    }): Promise<Fiduciary> => {
      return this.request("POST", "/api/v1/fiduciaries", { body: data });
    },

    regenerateApiKey: async (id: string): Promise<{ api_key: string }> => {
      return this.request("POST", `/api/v1/fiduciaries/${id}/regenerate-key`);
    },
  };

  readonly principals = {
    get: async (id: string): Promise<DataPrincipal> => {
      return this.request("GET", `/api/v1/principals/${id}`);
    },

    getByWallet: async (walletAddress: string): Promise<DataPrincipal> => {
      return this.request("GET", "/api/v1/principals/by-wallet", {
        params: { wallet_address: walletAddress },
      });
    },
  };

  readonly webhooks = {
    list: async (fiduciaryId: string): Promise<WebhookSubscription[]> => {
      return this.request("GET", `/api/v1/fiduciaries/${fiduciaryId}/webhooks`);
    },

    create: async (
      fiduciaryId: string,
      data: {
        callback_url: string;
        events: string[];
        secret: string;
      },
    ): Promise<WebhookSubscription> => {
      return this.request(
        "POST",
        `/api/v1/fiduciaries/${fiduciaryId}/webhooks`,
        { body: data },
      );
    },

    deliveries: async (subscriptionId: string): Promise<WebhookDelivery[]> => {
      return this.request(
        "GET",
        `/api/v1/webhooks/${subscriptionId}/deliveries`,
      );
    },
  };

  readonly stats = {
    dashboard: async (): Promise<DashboardStats> => {
      return this.request("GET", "/api/v1/consents/stats");
    },
  };

  readonly grievances = {
    list: async (params?: { status?: string }): Promise<Grievance[]> => {
      return this.request("GET", "/api/v1/grievances", { params });
    },

    get: async (id: string): Promise<Grievance> => {
      return this.request("GET", `/api/v1/grievances/${id}`);
    },

    create: async (data: {
      principal_id: string;
      fiduciary_id: string;
      type: string;
      description: string;
    }): Promise<Grievance> => {
      return this.request("POST", "/api/v1/grievances", { body: data });
    },

    resolve: async (id: string, resolution: string): Promise<Grievance> => {
      return this.request("POST", `/api/v1/grievances/${id}/resolve`, {
        body: { resolution },
      });
    },
  };

  readonly templates = {
    list: async (language?: string): Promise<ConsentTemplate[]> => {
      return this.request("GET", "/api/v1/templates", { params: { language } });
    },

    get: async (id: string): Promise<ConsentTemplate> => {
      return this.request("GET", `/api/v1/templates/${id}`);
    },
  };

  readonly reports = {
    generate: async (
      fiduciaryId: string,
      params: {
        period_start: string;
        period_end: string;
      },
    ): Promise<ComplianceReport> => {
      return this.request(
        "POST",
        `/api/v1/fiduciaries/${fiduciaryId}/reports`,
        { body: params },
      );
    },

    get: async (id: string): Promise<ComplianceReport> => {
      return this.request("GET", `/api/v1/reports/${id}`);
    },

    downloadPdf: async (id: string): Promise<Blob> => {
      const response = await fetch(`${this.baseUrl}/api/v1/reports/${id}/pdf`, {
        headers: this.apiKey ? { "X-API-Key": this.apiKey } : {},
      });
      return response.blob();
    },
  };
}

export default ConsentChainClient;
