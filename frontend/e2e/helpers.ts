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
