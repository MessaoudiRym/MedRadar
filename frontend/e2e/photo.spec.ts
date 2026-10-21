import { expect, test } from "@playwright/test";

import { GLUCOPHAGE_850 } from "./config";
import { readTestBox } from "./helpers";

// The API runs with the simulated reader (scripts/run_e2e_api.py): no real model is called.

test("a photo of the box leads to the medicine page after confirmation", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Take a photo of the box" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Choose a photo from the gallery" })).toBeVisible();

  await page.getByTestId("photo-gallery").setInputFiles("e2e/fixtures/test-box.jpg");
  await expect(page.getByRole("img", { name: "Your photo of the medicine box" })).toBeVisible();
  await expect(page.getByText("Photograph the box, not the prescription.").first()).toBeVisible();
  await page.getByRole("button", { name: "Read this box" }).click();

  await expect(page.getByText("We read: GLUCOPHAGE 850 mg, comprimé pelliculé")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Is this your medicine?" })).toBeFocused();

  const first = page.getByRole("link").filter({ hasText: "Exact match" }).first();
  await expect(first).toContainText("Glucophage 850");
  await first.click();

  await expect(page).toHaveURL(new RegExp(`/medicament/${GLUCOPHAGE_850}$`));
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Glucophage 850");
});

test("after a photo, the patient can still type the name", async ({ page }) => {
  await page.goto("/");
  await readTestBox(page);
  await page.getByRole("button", { name: "None of these, I’ll type the name" }).click();
  await expect(page.getByRole("combobox", { name: "Name of the medicine or active ingredient" })).toBeFocused();
});

test("a file that is not a photo shows a clear message and keeps the search", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("photo-gallery").setInputFiles({
    name: "notes.jpg",
    mimeType: "image/jpeg",
    buffer: Buffer.from("this is not an image"),
  });
  await page.getByRole("button", { name: "Read this box" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "This file is not a photo we can read" })).toBeVisible();
  await page.getByRole("button", { name: "Type the name instead" }).click();
  await expect(page.getByRole("combobox", { name: "Name of the medicine or active ingredient" })).toBeFocused();
});
