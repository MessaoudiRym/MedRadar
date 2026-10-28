import { defineConfig, devices } from "@playwright/test";

// Light checks of the ONLINE version (nothing is started locally):
//   BASE_URL=https://medradar.vercel.app DEMO_PHARMACIST_PASSWORD=... npm run test:prod
// The demo pharmacist changes one stock, then puts it back as it was.
const BASE_URL = process.env.BASE_URL;
if (!BASE_URL) throw new Error("Set BASE_URL to the address of the site, e.g. https://medradar.vercel.app");

export default defineConfig({
  testDir: "./e2e",
  testMatch: /production\.spec\.ts/,
  fullyParallel: false,
  workers: 1,
  retries: 1,
  reporter: [["list"]],
  // The free API can take a minute to wake up
  timeout: 150_000,
  expect: { timeout: 70_000 },
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});
