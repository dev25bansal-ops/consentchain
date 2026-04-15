# E2E Tests

This directory contains Playwright end-to-end tests for ConsentChain.

## Setup

```bash
# Install dependencies
npm install

# Install Playwright browsers
npx playwright install

# Run tests
npm test

# Run tests with UI
npm run test:ui

# Run tests in debug mode
npm run test:debug
```

## Environment Variables

Create a `.env` file:

```env
E2E_BASE_URL=http://localhost:3000
E2E_API_URL=http://localhost:8001
TEST_API_KEY=your-test-api-key
```

## Test Structure

```
tests/
├── fixtures/
│   └── test-fixtures.ts    # Test helpers and fixtures
├── dashboard.spec.ts       # Dashboard UI tests
└── api.spec.ts             # API endpoint tests
```

## Running Tests

```bash
# Run all tests
npm test

# Run specific test file
npx playwright test dashboard.spec.ts

# Run tests in headed mode
npm run test:headed

# Generate test code
npm run codegen

# View test report
npm run test:report
```

## Test Categories

### Dashboard Tests (dashboard.spec.ts)

- Landing page
- Wallet connection
- Consent creation
- Consent management
- Settings
- Responsive design
- Accessibility

### API Tests (api.spec.ts)

- Health endpoints
- Authentication
- Consent operations
- Grievance operations
- Rate limiting
- Input validation
- OAuth integration
- i18n endpoints
- Analytics

## CI/CD

Tests run automatically in GitHub Actions on:

- Push to main branch
- Pull requests

## Writing Tests

```typescript
import { test, expect } from "@playwright/test";

test("should do something", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toBeVisible();
});
```

## Best Practices

1. Use data-testid attributes for selectors
2. Mock external services when possible
3. Test responsive design with viewport sizes
4. Include accessibility checks
5. Handle async operations properly
