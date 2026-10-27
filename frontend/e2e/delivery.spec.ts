import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

import { API_URL, DEMO_PHARMACIST, TAHOR_20 } from "./config";
import { login, scanDemoNote, sessionToken } from "./helpers";

// The API runs with the simulated reader (scripts/run_e2e_api.py): no real model is called.

/** No serious accessibility problem on the current screen (WCAG 2.1 A and AA). */
async function checkAccessibility(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(serious.map((v) => `${v.id}: ${v.help} (${v.nodes.length})`)).toEqual([]);
}

async function stockOf(page: Page, medicineId: string) {
  const response = await page.request.get(`${API_URL}/pharmacist/stock`, {
    headers: { Authorization: `Bearer ${await sessionToken(page)}` },
  });
  const item = (await response.json()).find((i: { medicament: { id: string } }) => i.medicament.id === medicineId);
  return item ? item.statut : null;
}

test("a pharmacist scans a delivery note, keeps it, finds it, then cancels it", async ({ page }) => {
  page.on("dialog", (dialog) => dialog.accept());
  await login(page, DEMO_PHARMACIST);
  await expect(page).toHaveURL(/\/pharmacien$/);
  const before = await stockOf(page, TAHOR_20);

  // Scan and review: the line to check gets a medicine chosen by the pharmacist
  await scanDemoNote(page);
  await expect(page.getByText("20 lines read")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Not delivered (2)" })).toBeVisible();
  await expect(page.getByText("Products outside the official list, ignored (1)")).toBeVisible();
  await checkAccessibility(page);
  await expect(page.getByRole("checkbox", { name: /Keep this note in my history/ })).toBeChecked();
  await page.getByRole("checkbox", { name: /Also keep the photo/ }).check();
  await page.getByRole("button", { name: "Put the 16 ticked medicines in stock" }).click();

  await expect(page.getByRole("heading", { name: "Stock updated" })).toBeVisible();
  await expect(page.getByText("Note saved in your history.")).toBeVisible();

  // In stock for patients
  const availability = await page.request.get(`${API_URL}/medicines/${TAHOR_20}/availability`, {
    params: { lat: 35.697, lng: -0.633, radius_km: 50 },
  });
  const inStock = (await availability.json()).resultats.flatMap((r: { en_stock: { nom: string }[] }) => r.en_stock);
  expect(inStock.map((p: { nom: string }) => p.nom)).toContain("Pharmacie Démo Bir El Djir 01");
  expect(await stockOf(page, TAHOR_20)).toBe("en_stock");

  // In the history, with its photo
  await page.getByRole("link", { name: "See this note" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Grossiste Démo Ouest");
  await expect(page.getByRole("img", { name: /Photo of the delivery note, page 1/ })).toBeVisible();
  await expect(page.getByRole("listitem").filter({ hasText: "TAHOR CP B/30" }).getByText("Corrected by you")).toBeVisible();

  // "When did I receive…?"
  await page.getByRole("link", { name: "All delivery notes" }).click();
  await page.getByLabel("When did I receive…?").fill("tahor 20");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByRole("link", { name: /N° BL-2026-10458/ }).first()).toBeVisible();
  await checkAccessibility(page);

  // Cancel within 24 hours: back to the previous status
  await page.getByRole("link", { name: /N° BL-2026-10458/ }).first().click();
  await page.getByRole("button", { name: "Cancel this note" }).click();
  await expect(page.getByText("Note cancelled")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Cancelled");
  expect(await stockOf(page, TAHOR_20)).toBe(before);
});
