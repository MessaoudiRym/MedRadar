// Screenshots for the README and the jury: npm run screenshots
// They are written to docs/screenshots/.

import { type Browser, devices, expect, type Page, test } from "@playwright/test";

import { DEMO_PHARMACIST, GLUCOPHAGE_850 } from "./config";
import { login, readTestBox, search } from "./helpers";

const OUT = "../docs/screenshots";
const SIZES = {
  desktop: { viewport: { width: 1280, height: 860 }, deviceScaleFactor: 1 },
  mobile: { ...devices["Pixel 7"] },
};

async function open(browser: Browser, size: keyof typeof SIZES): Promise<Page> {
  const context = await browser.newContext(SIZES[size]);
  return context.newPage();
}

async function settle(page: Page) {
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(800); // map tiles and fonts
}

for (const size of ["desktop", "mobile"] as const) {
  test(`home (${size})`, async ({ browser }) => {
    const page = await open(browser, size);
    await page.goto("/");
    await search(page, "glucofage");
    await settle(page);
    await page.screenshot({ path: `${OUT}/home-${size}.png`, fullPage: size === "desktop" });
  });

  test(`medicine page (${size})`, async ({ browser }) => {
    const page = await open(browser, size);
    await page.goto(`/medicament/${GLUCOPHAGE_850}`);
    await expect(page.locator(".marker-pin--stock").first()).toBeVisible();
    await settle(page);
    await page.screenshot({ path: `${OUT}/medicine-${size}.png`, fullPage: size === "desktop" });
    if (size === "mobile") {
      // Second screen on a phone: a pharmacy card, then the map
      await page.getByRole("region", { name: "Available near you" }).getByRole("listitem").first().scrollIntoViewIfNeeded();
      await page.mouse.wheel(0, 120);
      await settle(page);
      await page.screenshot({ path: `${OUT}/medicine-mobile-pharmacies.png` });
      await page.locator(".leaflet-container").scrollIntoViewIfNeeded();
      await settle(page);
      await page.screenshot({ path: `${OUT}/medicine-mobile-map.png` });
    }
  });

  test(`photo confirmation (${size})`, async ({ browser }) => {
    const page = await open(browser, size);
    await page.goto("/");
    await readTestBox(page);
    const question = page.getByRole("heading", { name: "Is this your medicine?" });
    await expect(question).toBeVisible();
    await page.getByText("We read:").scrollIntoViewIfNeeded();
    await settle(page);
    await page.screenshot({ path: `${OUT}/photo-confirmation-${size}.png`, fullPage: size === "desktop" });
  });

  test(`pharmacist dashboard (${size})`, async ({ browser }) => {
    const page = await open(browser, size);
    await login(page, DEMO_PHARMACIST);
    await expect(page.getByRole("heading", { name: "Your stock" })).toBeVisible();
    // Tall enough to show the first medicines and their buttons
    if (size === "desktop") await page.setViewportSize({ width: 1280, height: 1250 });
    await settle(page);
    await page.screenshot({ path: `${OUT}/dashboard-${size}.png`, fullPage: false });
  });
}
