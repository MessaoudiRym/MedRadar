import { expect, type Page } from "@playwright/test";

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
