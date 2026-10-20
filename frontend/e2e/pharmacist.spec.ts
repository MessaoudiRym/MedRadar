import { expect, test } from "@playwright/test";

import { DEMO_PHARMACIST } from "./config";
import { login } from "./helpers";

test("a demo pharmacist marks a medicine out of stock, then in stock", async ({ page }) => {
  await login(page, DEMO_PHARMACIST);
  await expect(page).toHaveURL(/\/pharmacien$/);
  await expect(page.getByText("Approved: patients can see your pharmacy")).toBeVisible();

  const row = page.getByRole("listitem").filter({ has: page.getByRole("group", { name: /^Stock of/ }) }).first();
  const name = (await row.getByRole("heading").textContent()) ?? "";

  await row.getByRole("button", { name: "Out of stock", exact: true }).click();
  await expect(row.getByText("Saved: out of stock.")).toBeVisible();
  await expect(row.getByRole("button", { name: "Out of stock", exact: true })).toHaveAttribute("aria-pressed", "true");

  await row.getByRole("button", { name: "In stock", exact: true }).click();
  await expect(row.getByText("Saved: in stock.")).toBeVisible();

  // Saved in the API: still in stock after reloading the page
  await page.reload();
  const again = page.getByRole("listitem").filter({ has: page.getByRole("heading", { name, exact: true }) });
  await expect(again.getByRole("button", { name: "In stock", exact: true })).toHaveAttribute("aria-pressed", "true");
});

test("registration with an invalid phone shows an error", async ({ page }) => {
  await page.goto("/pharmacien/inscription");
  await page.getByLabel("Email").fill("new-pharmacist@example.com");
  await page.getByLabel("Password", { exact: true }).fill("Pharma2026x");
  await page.getByLabel("First name").fill("Amina");
  await page.getByLabel("Last name").fill("Test");
  await page.getByLabel("Your mobile phone").fill("0812 34");
  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page.getByText("Enter an Algerian number, e.g. 0550 12 34 56 or 041 23 45 67.")).toBeVisible();
  await expect(page.getByLabel("Your mobile phone")).toHaveAttribute("aria-invalid", "true");
  await expect(page.getByText("Step 1 of 2")).toBeVisible();
});

test("the dashboard needs a login", async ({ page }) => {
  await page.goto("/pharmacien");
  await expect(page).toHaveURL(/\/pharmacien\/connexion$/);
});
