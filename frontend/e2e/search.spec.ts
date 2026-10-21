import { expect, test } from "@playwright/test";

import { searchAndValidate } from "./helpers";

// The API runs with the simulated interpreter (scripts/run_e2e_api.py): no real model is called.

test("an Arabic brand name is understood, and its page opens", async ({ page }) => {
  await page.goto("/");
  await searchAndValidate(page, "غلوكوفاج");

  await expect(page).toHaveURL(/\/recherche\?q=/);
  const banner = page.getByText("we understood:");
  await expect(banner).toContainText("You wrote “غلوكوفاج” — we understood: GLUCOPHAGE.");
  await expect(page.locator('bdi[lang="ar"]').first()).toHaveText("غلوكوفاج");

  await page.getByRole("link", { name: /Glucophage/ }).first().click();
  await expect(page).toHaveURL(/\/medicament\//);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Glucophage");
});

test("a disease never gives a medicine", async ({ page }) => {
  await page.goto("/");
  await searchAndValidate(page, "دوا السكر");
  await expect(page.getByText("MedRadar does not choose a medicine from a disease or a symptom")).toBeVisible();
  await expect(page.getByRole("link", { name: /Glucophage|Metformine/i })).toHaveCount(0);
});

test("the Search button and suggestions still work in French", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("combobox", { name: "Name of the medicine or active ingredient" }).fill("glucofage");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("result");
  await expect(page.getByRole("link", { name: /Glucophage 850/ })).toBeVisible();
  await expect(page.getByText("we understood:")).toHaveCount(0); // found by the normal search
});

test("a foreign brand shows its molecule, to check", async ({ page }) => {
  await page.goto("/");
  await searchAndValidate(page, "Tylenol");
  await expect(page.getByText("Not sold in Algeria under this name", { exact: true })).toBeVisible();
  await expect(page.getByText("Check that this is your medicine before continuing.")).toBeVisible();
});
