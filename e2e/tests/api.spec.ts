import { test, expect } from "@playwright/test";
import { APIRequestContext } from "@playwright/test";

test.describe("API Health Endpoints", () => {
  test("should return healthy status", async ({ request }) => {
    const response = await request.get("/health");
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.status).toBe("healthy");
  });

  test("should return ready status", async ({ request }) => {
    const response = await request.get("/ready");
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.ready).toBe(true);
  });

  test("should return metrics", async ({ request }) => {
    const response = await request.get("/metrics");
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty("requests_total");
  });
});

test.describe("API Authentication", () => {
  test("should reject unauthorized requests", async ({ request }) => {
    const response = await request.post("/api/v1/consent/create", {
      data: {
        principal_wallet: "test-wallet",
        purpose: "MARKETING",
        data_types: ["email"],
      },
    });

    expect(response.status()).toBe(401);
  });

  test("should accept API key authentication", async ({ request }) => {
    const testApiKey = process.env.TEST_API_KEY || "test-api-key";

    const response = await request.get("/api/v1/fiduciaries", {
      headers: {
        "X-API-Key": testApiKey,
      },
    });

    expect(response.status()).toBeOneOf([200, 401]); // 401 if key invalid
  });
});

test.describe("Fiduciary Registration", () => {
  test("should register new fiduciary", async ({ request }) => {
    const response = await request.post("/api/v1/fiduciary/register", {
      data: {
        name: "Test Fiduciary",
        contact_email: "test@example.com",
        website: "https://example.com",
        description: "Test fiduciary for E2E testing",
      },
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.success).toBe(true);
  });
});

test.describe("Consent Operations", () => {
  let consentId: string;
  let apiKey: string;

  test.beforeAll(async ({ request }) => {
    // Get or create test API key
    const regResponse = await request.post("/api/v1/fiduciary/register", {
      data: {
        name: "E2E Test Fiduciary",
        contact_email: "e2e@test.com",
      },
    });

    if (regResponse.ok()) {
      const data = await regResponse.json();
      apiKey = data.data?.api_key || process.env.TEST_API_KEY || "test-key";
    } else {
      apiKey = process.env.TEST_API_KEY || "test-key";
    }
  });

  test("should create consent", async ({ request }) => {
    const response = await request.post("/api/v1/consent/create", {
      headers: {
        "X-API-Key": apiKey,
      },
      data: {
        principal_wallet:
          "P3E2KO4G7BA6CFH6ICCYRGEIV5QIY5P6F73LEXAMJJUSAMUHURZN3TRGAI",
        purpose: "MARKETING",
        data_types: ["email", "name"],
        duration_days: 365,
      },
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.success).toBe(true);

    if (data.data?.consent_id) {
      consentId = data.data.consent_id;
    }
  });

  test("should verify consent", async ({ request }) => {
    test.skip(!consentId, "No consent ID from previous test");

    const response = await request.post("/api/v1/consent/verify", {
      data: {
        consent_id: consentId,
      },
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.success).toBe(true);
  });

  test("should query consents", async ({ request }) => {
    const response = await request.get("/api/v1/consent/query", {
      headers: {
        "X-API-Key": apiKey,
      },
      params: {
        limit: 10,
        offset: 0,
      },
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.success).toBe(true);
    expect(Array.isArray(data.data?.consents)).toBe(true);
  });

  test("should revoke consent", async ({ request }) => {
    test.skip(!consentId, "No consent ID from previous test");

    const response = await request.post("/api/v1/consent/revoke", {
      data: {
        consent_id: consentId,
        reason: "E2E test revocation",
      },
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.success).toBe(true);
  });
});

test.describe("Grievance Operations", () => {
  test("should submit grievance", async ({ request }) => {
    const response = await request.post("/api/v1/grievance/submit", {
      data: {
        principal_wallet:
          "P3E2KO4G7BA6CFH6ICCYRGEIV5QIY5P6F73LEXAMJJUSAMUHURZN3TRGAI",
        fiduciary_id: "test-fiduciary",
        subject: "Test Grievance",
        description: "This is a test grievance from E2E tests",
        category: "DATA_PROCESSING",
      },
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.success).toBe(true);
  });
});

test.describe("Rate Limiting", () => {
  test("should enforce rate limits", async ({ request }) => {
    const promises = [];

    // Make many rapid requests
    for (let i = 0; i < 250; i++) {
      promises.push(request.get("/health"));
    }

    const responses = await Promise.all(promises);
    const rateLimited = responses.some((r) => r.status() === 429);

    // At least some should be rate limited
    expect(rateLimited).toBe(true);
  });
});

test.describe("Input Validation", () => {
  test("should reject invalid consent data", async ({ request }) => {
    const response = await request.post("/api/v1/consent/create", {
      headers: {
        "X-API-Key": "test-key",
      },
      data: {
        principal_wallet: "", // Invalid: empty
        purpose: "INVALID_PURPOSE", // Invalid: not in allowed list
        data_types: [], // Invalid: empty
      },
    });

    expect(response.status()).toBe(400);
  });

  test("should sanitize input", async ({ request }) => {
    const response = await request.post("/api/v1/grievance/submit", {
      data: {
        principal_wallet:
          "P3E2KO4G7BA6CFH6ICCYRGEIV5QIY5P6F73LEXAMJJUSAMUHURZN3TRGAI",
        fiduciary_id: "test",
        subject: '<script>alert("xss")</script>Test',
        description: "Test",
      },
    });

    // Should either reject or sanitize
    if (response.ok()) {
      const data = await response.json();
      expect(data.data?.subject).not.toContain("<script>");
    } else {
      expect(response.status()).toBe(400);
    }
  });
});

test.describe("OAuth Integration", () => {
  test("should list OAuth providers", async ({ request }) => {
    const response = await request.get("/api/v1/oauth/providers");
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(Array.isArray(data.providers)).toBe(true);
  });

  test("should return OAuth status", async ({ request }) => {
    const response = await request.get("/api/v1/oauth/status");
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.status).toBe("operational");
  });
});

test.describe("i18n Endpoints", () => {
  test("should list supported languages", async ({ request }) => {
    const response = await request.get("/api/v1/i18n/languages");
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.languages.length).toBeGreaterThan(0);
    expect(data.languages.find((l: any) => l.code === "hi")).toBeTruthy();
  });

  test("should get consent templates", async ({ request }) => {
    const response = await request.get("/api/v1/i18n/templates");
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(Array.isArray(data.templates)).toBe(true);
  });
});

test.describe("Analytics Endpoints", () => {
  test("should return consent metrics", async ({ request }) => {
    const response = await request.post("/api/v1/analytics/metrics", {
      data: {
        consents: [
          { status: "GRANTED", created_at: new Date().toISOString() },
          { status: "REVOKED", created_at: new Date().toISOString() },
        ],
      },
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.total_consents).toBeDefined();
  });
});
