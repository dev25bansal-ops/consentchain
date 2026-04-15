import { test as base, Page, expect } from "@playwright/test";

interface ConsentChainFixtures {
  authenticatedPage: Page;
  apiContext: any;
}

export const test = base.extend<ConsentChainFixtures>({
  authenticatedPage: async ({ page }, use) => {
    // Mock wallet connection for testing
    await page.addInitScript(() => {
      window.localStorage.setItem("test_wallet_connected", "true");
      window.localStorage.setItem(
        "test_wallet_address",
        "P3E2KO4G7BA6CFH6ICCYRGEIV5QIY5P6F73LEXAMJJUSAMUHURZN3TRGAI",
      );
    });
    await use(page);
  },

  apiContext: async ({ playwright }, use) => {
    const context = await playwright.request.newContext({
      baseURL: process.env.E2E_API_URL || "http://localhost:8001",
    });
    await use(context);
  },
});

export { expect };

// Test utilities
export class ConsentChainHelper {
  constructor(private page: Page) {}

  async waitForDashboardLoad() {
    await this.page.waitForSelector('[data-testid="dashboard-container"]', {
      timeout: 30000,
    });
  }

  async connectWallet() {
    await this.page.click('[data-testid="connect-wallet-button"]');
    await this.page.waitForSelector('[data-testid="wallet-connected"]', {
      timeout: 10000,
    });
  }

  async createConsent(data: {
    purpose: string;
    dataTypes: string[];
    fiduciary: string;
    duration: number;
  }) {
    await this.page.click('[data-testid="create-consent-button"]');
    await this.page.fill('[data-testid="purpose-input"]', data.purpose);
    await this.page.fill('[data-testid="fiduciary-input"]', data.fiduciary);

    for (const type of data.dataTypes) {
      await this.page.check(`[data-testid="datatype-${type}"]`);
    }

    await this.page.fill(
      '[data-testid="duration-input"]',
      data.duration.toString(),
    );
    await this.page.click('[data-testid="submit-consent"]');

    await this.page.waitForSelector('[data-testid="consent-created-success"]', {
      timeout: 10000,
    });
  }

  async verifyConsent(consentId: string) {
    await this.page.click('[data-testid="view-consent"]');
    await this.page.fill('[data-testid="search-consent"]', consentId);
    await this.page.waitForSelector(`[data-testid="consent-${consentId}"]`, {
      timeout: 10000,
    });
  }

  async revokeConsent(consentId: string) {
    await this.page.click(`[data-testid="consent-${consentId}"]`);
    await this.page.click('[data-testid="revoke-consent-button"]');
    await this.page.waitForSelector('[data-testid="consent-revoked-success"]', {
      timeout: 10000,
    });
  }
}

// Test data generators
export function generateTestConsent() {
  return {
    purpose: "MARKETING",
    dataTypes: ["email", "name"],
    fiduciary: "Test Company Inc.",
    duration: 365,
  };
}

export function generateTestPrincipal() {
  return {
    walletAddress: "P3E2KO4G7BA6CFH6ICCYRGEIV5QIY5P6F73LEXAMJJUSAMUHURZN3TRGAI",
    email: `test-${Date.now()}@example.com`,
    name: "Test User",
  };
}
