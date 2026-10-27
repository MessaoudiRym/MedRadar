import { expect, type Page } from "@playwright/test";

import { TEST_BOX_PHOTO } from "./config";

export async function login(page: Page, account: { email: string; password: string }) {
  await page.goto("/pharmacien/connexion");
  await page.getByLabel("Email").fill(account.email);
  await page.getByLabel("Password", { exact: true }).fill(account.password);
  await page.getByRole("button", { name: "Log in" }).click();
}

export async function search(page: Page, text: string) {
  const box = page.getByRole("combobox", { name: "Name of the medicine or active ingredient" });
  await box.fill(text);
  await expect(page.getByRole("listbox")).toBeVisible();
}

/** Choose the test photo from the gallery, then send it. */
export async function readTestBox(page: Page) {
  await page.getByTestId("photo-gallery").setInputFiles(TEST_BOX_PHOTO);
  await expect(page.getByRole("img", { name: "Your photo of the medicine box" })).toBeVisible();
  await page.getByRole("button", { name: "Read this box" }).click();
}

/** Type a query and validate it with Enter (full search, which may use the language model). */
export async function searchAndValidate(page: Page, text: string) {
  const box = page.getByRole("combobox", { name: "Name of the medicine or active ingredient" });
  await box.fill(text);
  await box.press("Enter");
  await expect(page).toHaveURL(/\/recherche\?q=/);
}

/** Token of the logged-in user, to check the API directly (no extra login). */
export async function sessionToken(page: Page): Promise<string> {
  const raw = await page.evaluate(() => sessionStorage.getItem("medradar.session"));
  return JSON.parse(raw ?? "{}").token;
}

/** From the dashboard: scan the demo note, choose TAHOR 20 mg for the line to check. */
export async function scanDemoNote(page: Page) {
  await page.getByRole("link", { name: "Scan a delivery note" }).first().click();
  await expect(page).toHaveURL(/\/pharmacien\/scanner$/);
  await page.getByRole("button", { name: "Try with a demo delivery note" }).click();
  await expect(page.getByRole("img", { name: "Page 1 of the delivery note" })).toBeVisible();
  await page.getByRole("button", { name: "Read the note (1 page)" }).click();
  await expect(page.getByRole("heading", { name: "Check the note" })).toBeVisible();
  const tahor = page.getByRole("listitem").filter({ hasText: "TAHOR CP B/30" });
  // The choice replaces the list of candidates by the chosen medicine
  await tahor.getByRole("radio", { name: /Tahor 20 mg/ }).click();
  await expect(tahor.getByText("Chosen by you")).toBeVisible();
}
