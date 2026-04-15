import { test, expect } from "../fixtures/test-fixtures";
import {
  ConsentChainHelper,
  generateTestConsent,
  generateTestPrincipal,
} from "../fixtures/test-fixtures";

test.describe("Dashboard Landing Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("should display landing page", async ({ page }) => {
    await expect(page.locator("h1")).toContainText("ConsentChain");
    await expect(
      page.locator('[data-testid="connect-wallet-button"]'),
    ).toBeVisible();
  });

  test("should display feature highlights", async ({ page }) => {
    await expect(page.locator("text=DPDP Compliant")).toBeVisible();
    await expect(page.locator("text=Blockchain")).toBeVisible();
    await expect(page.locator("text=Consent Management")).toBeVisible();
  });

  test("should show connect wallet prompt", async ({ page }) => {
    const connectButton = page.locator('[data-testid="connect-wallet-button"]');
    await expect(connectButton).toBeVisible();
    await expect(connectButton).toContainText("Connect Wallet");
  });
});

test.describe("Wallet Connection Flow", () => {
  test("should show wallet options on click", async ({ page }) => {
    await page.goto("/");
    await page.click('[data-testid="connect-wallet-button"]');

    // Should show wallet provider options
    await expect(page.locator("text=Pera Wallet")).toBeVisible();
    await expect(page.locator("text=Exodus")).toBeVisible();
  });

  test("should display wallet address after connection", async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto("/");
    await expect(
      authenticatedPage.locator('[data-testid="wallet-address"]'),
    ).toBeVisible();
    await expect(
      authenticatedPage.locator('[data-testid="wallet-address"]'),
    ).toContainText(
      "P3E2KO4G7BA6CFH6ICCYRGEIV5QIY5P6F73LEXAMJJUSAMUHURZN3TRGAI",
    );
  });
});

test.describe("Dashboard Main View", () => {
  test.use({ storageState: ".auth/user.json" });

  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector('[data-testid="dashboard-container"]');
  });

  test("should display consent summary", async ({ page }) => {
    await expect(page.locator('[data-testid="total-consents"]')).toBeVisible();
    await expect(page.locator('[data-testid="active-consents"]')).toBeVisible();
    await expect(
      page.locator('[data-testid="expired-consents"]'),
    ).toBeVisible();
  });

  test("should show navigation menu", async ({ page }) => {
    await expect(page.locator('[data-testid="nav-consents"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-history"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-settings"]')).toBeVisible();
  });

  test("should display recent consents list", async ({ page }) => {
    await expect(page.locator('[data-testid="recent-consents"]')).toBeVisible();
    await expect(
      page.locator('[data-testid="consent-list-item"]').first(),
    ).toBeVisible();
  });
});

test.describe("Consent Creation", () => {
  test.use({ storageState: ".auth/user.json" });

  test("should open create consent modal", async ({ page }) => {
    await page.goto("/");
    await page.click('[data-testid="create-consent-button"]');

    await expect(
      page.locator('[data-testid="create-consent-modal"]'),
    ).toBeVisible();
  });

  test("should validate consent form fields", async ({ page }) => {
    await page.goto("/");
    await page.click('[data-testid="create-consent-button"]');

    // Try to submit without filling
    await page.click('[data-testid="submit-consent"]');

    // Should show validation errors
    await expect(page.locator("text=Purpose is required")).toBeVisible();
  });

  test("should create consent successfully", async ({ page }) => {
    const helper = new ConsentChainHelper(page);
    const testData = generateTestConsent();

    await page.goto("/");
    await helper.createConsent(testData);

    await expect(
      page.locator('[data-testid="consent-created-success"]'),
    ).toBeVisible();
  });

  test("should show consent details after creation", async ({ page }) => {
    const helper = new ConsentChainHelper(page);
    const testData = generateTestConsent();

    await page.goto("/");
    await helper.createConsent(testData);

    await page.click('[data-testid="view-new-consent"]');

    await expect(page.locator(`text=${testData.purpose}`)).toBeVisible();
    await expect(page.locator(`text=${testData.fiduciary}`)).toBeVisible();
  });
});

test.describe("Consent Management", () => {
  test.use({ storageState: ".auth/user.json" });

  test("should display consent details", async ({ page }) => {
    await page.goto("/");
    await page.click('[data-testid="consent-list-item"]').first();

    await expect(
      page.locator('[data-testid="consent-detail-view"]'),
    ).toBeVisible();
    await expect(page.locator('[data-testid="consent-purpose"]')).toBeVisible();
    await expect(page.locator('[data-testid="consent-status"]')).toBeVisible();
  });

  test("should revoke consent", async ({ page }) => {
    await page.goto("/");
    await page.click('[data-testid="consent-list-item"]').first();
    await page.click('[data-testid="revoke-consent-button"]');

    // Confirmation modal
    await expect(
      page.locator('[data-testid="revoke-confirmation-modal"]'),
    ).toBeVisible();
    await page.click('[data-testid="confirm-revoke"]');

    await expect(
      page.locator('[data-testid="consent-revoked-success"]'),
    ).toBeVisible();
  });

  test("should modify consent", async ({ page }) => {
    await page.goto("/");
    await page.click('[data-testid="consent-list-item"]').first();
    await page.click('[data-testid="modify-consent-button"]');

    await page.fill('[data-testid="duration-input"]', "180");
    await page.click('[data-testid="submit-modification"]');

    await expect(
      page.locator('[data-testid="consent-modified-success"]'),
    ).toBeVisible();
  });
});

test.describe("Consent Verification", () => {
  test("should verify valid consent", async ({ apiContext }) => {
    const response = await apiContext.get("/api/v1/consent/test-consent-id");
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.success).toBe(true);
  });
});

test.describe("Settings Page", () => {
  test.use({ storageState: ".auth/user.json" });

  test("should display settings options", async ({ page }) => {
    await page.goto("/");
    await page.click('[data-testid="nav-settings"]');

    await expect(
      page.locator('[data-testid="settings-notifications"]'),
    ).toBeVisible();
    await expect(
      page.locator('[data-testid="settings-privacy"]'),
    ).toBeVisible();
  });

  test("should toggle notification preferences", async ({ page }) => {
    await page.goto("/");
    await page.click('[data-testid="nav-settings"]');

    const toggle = page.locator('[data-testid="email-notifications-toggle"]');
    await toggle.click();

    await expect(page.locator('[data-testid="settings-saved"]')).toBeVisible();
  });
});

test.describe("Responsive Design", () => {
  test("should display correctly on mobile", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/");

    await expect(
      page.locator('[data-testid="mobile-menu-button"]'),
    ).toBeVisible();
  });

  test("should show mobile navigation", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/");

    await page.click('[data-testid="mobile-menu-button"]');
    await expect(page.locator('[data-testid="mobile-nav-menu"]')).toBeVisible();
  });
});

test.describe("Error Handling", () => {
  test("should show error toast on API failure", async ({ page }) => {
    // Mock API failure
    await page.route("**/api/v1/**", (route) => route.abort("failed"));

    await page.goto("/");
    await page.click('[data-testid="create-consent-button"]');

    await expect(page.locator('[data-testid="error-toast"]')).toBeVisible();
  });

  test("should handle network timeout gracefully", async ({ page }) => {
    await page.route("**/api/v1/**", (route) => {
      return new Promise((resolve) => setTimeout(resolve, 60000));
    });

    await page.goto("/");

    await expect(page.locator('[data-testid="timeout-error"]')).toBeVisible({
      timeout: 45000,
    });
  });
});

test.describe("Accessibility", () => {
  test("should have no accessibility violations on landing", async ({
    page,
  }) => {
    await page.goto("/");

    // Basic accessibility checks
    await expect(page.locator("h1")).toBeVisible();

    // Check for alt text on images
    const images = await page.locator("img").all();
    for (const img of images) {
      await expect(img).toHaveAttribute("alt");
    }

    // Check for proper heading hierarchy
    const h1Count = await page.locator("h1").count();
    expect(h1Count).toBe(1);
  });

  test("should be keyboard navigable", async ({ page }) => {
    await page.goto("/");

    // Tab through the page
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");

    // Should be able to activate Connect Wallet with Enter
    await page.keyboard.press("Enter");

    await expect(page.locator('[data-testid="wallet-modal"]')).toBeVisible();
  });
});

test.describe("Performance", () => {
  test("should load dashboard within 3 seconds", async ({ page }) => {
    const startTime = Date.now();
    await page.goto("/");
    await page.waitForSelector('[data-testid="dashboard-container"]');
    const loadTime = Date.now() - startTime;

    expect(loadTime).toBeLessThan(3000);
  });

  test("should lazy load consent list", async ({ page }) => {
    await page.goto("/");

    // First consent should load immediately
    await expect(
      page.locator('[data-testid="consent-list-item"]').first(),
    ).toBeVisible();

    // Scroll to trigger lazy loading
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

    // More items should load
    const count = await page
      .locator('[data-testid="consent-list-item"]')
      .count();
    expect(count).toBeGreaterThan(1);
  });
});
