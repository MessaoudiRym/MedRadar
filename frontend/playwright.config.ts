import { defineConfig, devices } from "@playwright/test";

import { ADMIN, API_PORT, API_URL, DEMO_PASSWORD, WEB_PORT, WEB_URL } from "./e2e/config";

// End-to-end tests: Playwright starts the API (fresh demo database) and a
// production build of the frontend, then drives a real browser.
//   npm run test:e2e      desktop and mobile tests
//   npm run screenshots   screenshots in docs/screenshots/
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1, // the tests share one database
  retries: 0,
  reporter: [["list"]],
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: WEB_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] }, testIgnore: /screenshots|production/ },
    { name: "mobile", use: { ...devices["Pixel 7"] }, testIgnore: /screenshots|production/ },
    { name: "screenshots", use: { ...devices["Desktop Chrome"] }, testMatch: /screenshots\.spec\.ts/ },
  ],
  webServer: [
    {
      command: "python ../scripts/run_e2e_api.py",
      url: `${API_URL}/health`,
      timeout: 180_000,
      reuseExistingServer: false,
      env: {
        E2E_API_PORT: String(API_PORT),
        E2E_FRONTEND_URL: WEB_URL,
        ADMIN_EMAIL: ADMIN.email,
        ADMIN_PASSWORD: ADMIN.password,
        DEMO_PHARMACIST_PASSWORD: DEMO_PASSWORD,
        PYTHONIOENCODING: "utf-8",
      },
    },
    {
      // Built into .next-e2e so the normal build is never overwritten
      command: `npm run build && npx next start --port ${WEB_PORT}`,
      url: WEB_URL,
      timeout: 300_000,
      reuseExistingServer: false,
      env: { NEXT_DIST_DIR: ".next-e2e", NEXT_PUBLIC_API_URL: API_URL },
    },
  ],
});
