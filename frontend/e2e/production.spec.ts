// Checks of the online version: npm run test:prod (see playwright.production.config.ts).

import { expect, test } from "@playwright/test";

import { GLUCOPHAGE_850 } from "./config";
import { login, search } from "./helpers";

const DEMO = {
  email: process.env.DEMO_PHARMACIST_EMAIL || "pharmacien1@medradar.demo",
  password: process.env.DEMO_PHARMACIST_PASSWORD ?? "",
};

test("patient: search with a typo, then equivalents, pharmacies and map", async ({ page }) => {
  await page.goto("/");
  await search(page, "glucofage");
  await page.getByRole("option", { name: /Glucophage 850/ }).click();

  await expect(page).toHaveURL(new RegExp(`/medicament/${GLUCOPHAGE_850}$`));
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Glucophage 850");
  const equivalents = page.getByRole("region", { name: "Equivalents registered in Algeria" });
  await expect(equivalents.getByRole("link")).toHaveCount(13);
  const nearby = page.getByRole("region", { name: "Available near you" });
  await expect(nearby.getByRole("link", { name: /^Call/ }).first()).toBeVisible();
  await expect(page.locator(".leaflet-container")).toBeVisible();
});

test("the testing guide opens", async ({ page }) => {
  await page.goto("/demo");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Testing guide");
  await expect(page.getByRole("tab", { name: "Français" })).toBeVisible();
});

test("demo pharmacist: changes a stock, then puts it back", async ({ page }) => {
  test.skip(!DEMO.password, "DEMO_PHARMACIST_PASSWORD is not set");
  await login(page, DEMO);
  await expect(page).toHaveURL(/\/pharmacien$/);
  await expect(page.getByText("Approved: patients can see your pharmacy")).toBeVisible();

  const row = page.getByRole("listitem").filter({ has: page.getByRole("group", { name: /^Stock of/ }) }).first();
  const inStock = row.getByRole("button", { name: "In stock", exact: true });
  const outOfStock = row.getByRole("button", { name: "Out of stock", exact: true });
  const wasInStock = (await inStock.getAttribute("aria-pressed")) === "true";
  const [other, original] = wasInStock ? [outOfStock, inStock] : [inStock, outOfStock];

  await other.click();
  await expect(other).toHaveAttribute("aria-pressed", "true");
  await expect(row.getByText(/^Saved:/)).toBeVisible();

  // Back as it was, so the demo stays the same for the next visitor
  await original.click();
  await expect(original).toHaveAttribute("aria-pressed", "true");
});
