// API Service Layer
// Centralized API calls with proper typing, error handling, and request/response interceptors

import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from "axios";
import type {
  ApiResponse,
  Consent,
  ConsentQueryParams,
  ConsentCreateRequest,
  ConsentRevokeRequest,
  DashboardStats,
  ConsentEvent,
} from "../types";

const API_BASE_URL = "http://localhost:8001";

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        "Content-Type": "application/json",
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem("jwt_token");
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error),
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          localStorage.removeItem("jwt_token");
          window.location.href = "/";
        }
        return Promise.reject(error);
      },
    );
  }

  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    const response = await this.client.get("/health");
    return response.data;
  }

  // Consent endpoints
  async getConsents(params: ConsentQueryParams = {}): Promise<
    ApiResponse<{
      consents: Consent[];
      page: number;
      limit: number;
      total: number;
    }>
  > {
    if (params.principal_wallet) {
      const response = await this.client.get(
        `/api/v1/public/consent/${params.principal_wallet}`,
        {
          params: {
            status: params.status,
            page: params.page,
            limit: params.limit,
          },
        },
      );
      return response.data;
    }
    const response = await this.client.get("/api/v1/consent/query", { params });
    return response.data;
  }

  async getConsentById(consentId: string): Promise<ApiResponse<Consent>> {
    const response = await this.client.get(`/api/v1/consent/${consentId}`);
    return response.data;
  }

  async createConsent(
    data: ConsentCreateRequest,
  ): Promise<ApiResponse<Consent>> {
    const response = await this.client.post(
      "/api/v1/public/consent/create",
      data,
    );
    return response.data;
  }

  async revokeConsent(
    data: ConsentRevokeRequest,
  ): Promise<ApiResponse<Consent>> {
    const response = await this.client.post("/api/v1/consent/revoke", data);
    return response.data;
  }

  async verifyConsent(
    consentId: string,
    principalId?: string,
  ): Promise<ApiResponse<{ verified: boolean; message: string }>> {
    const response = await this.client.post("/api/v1/consent/verify", {
      consent_id: consentId,
      principal_id: principalId,
    });
    return response.data;
  }

  async getConsentHistory(
    consentId: string,
  ): Promise<ApiResponse<{ events: ConsentEvent[] }>> {
    const response = await this.client.get(
      `/api/v1/consent/${consentId}/history`,
    );
    return response.data;
  }

  // Metrics endpoint
  async getMetrics(): Promise<ApiResponse<DashboardStats>> {
    const response = await this.client.get("/api/v1/metrics");
    return response.data;
  }

  // Templates endpoint
  async getTemplates(): Promise<
    ApiResponse<{
      templates: Array<{
        id: string;
        name: string;
        language: string;
        category: string;
      }>;
    }>
  > {
    const response = await this.client.get("/api/v1/templates");
    return response.data;
  }

  // Generic request method for custom endpoints
  async request<T>(config: AxiosRequestConfig): Promise<T> {
    const response = await this.client.request<T>(config);
    return response.data;
  }
}

// Export singleton instance
export const apiService = new ApiService();

// Export class for testing purposes
export { ApiService };
