import { expect, test } from "@playwright/test";

import { ADMIN } from "./config";
import { login } from "./helpers";

// One login per project: the API allows 5 login attempts per minute
test("the admin approves a pharmacy waiting for verification", async ({ page }, testInfo) => {
  // Two demo pharmacies wait for verification: one per project (desktop, mobile)
  const name = testInfo.project.name === "mobile" ? "Pharmacie Démo Es Senia 42" : "Pharmacie Démo Bir El Djir 41";

  await login(page, ADMIN);
  await expect(page).toHaveURL(/\/admin$/);

  const card = page.getByRole("listitem").filter({ has: page.getByRole("heading", { name }) });
  await expect(card.getByText("Being verified")).toBeVisible();
  await card.getByRole("button", { name: "Approve" }).click();

  await expect(page.getByText(`${name}: approved`)).toBeVisible();
  await expect(card).toHaveCount(0);

  await page.getByRole("button", { name: "Approved", exact: true }).click();
  const approved = page.getByRole("listitem").filter({ has: page.getByRole("heading", { name }) });
  await expect(approved).toBeVisible();

  // Suspending needs a reason
  await approved.getByRole("button", { name: "Suspend" }).click();
  await approved.getByRole("button", { name: "Confirm the suspension" }).click();
  await expect(approved.getByText("Write a reason (at least 3 characters).")).toBeVisible();
  await approved.getByRole("button", { name: "Cancel" }).click();
});
