import { expect, test } from "@playwright/test";

import { GLUCOPHAGE_850 } from "./config";
import { search } from "./helpers";

test("a typo still finds the medicine, and its page opens", async ({ page }) => {
  await page.goto("/");
  await search(page, "glucofage");

  const option = page.getByRole("option", { name: /Glucophage 850/ });
  await expect(option).toBeVisible();
  await option.click();

  await expect(page).toHaveURL(new RegExp(`/medicament/${GLUCOPHAGE_850}$`));
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Glucophage 850");
  await expect(page).toHaveTitle(/Glucophage 850/);
});

test("the medicine page shows equivalents, nearby pharmacies and the map", async ({ page }) => {
  await page.goto(`/medicament/${GLUCOPHAGE_850}`);

  const equivalents = page.getByRole("region", { name: "Equivalents registered in Algeria" });
  await expect(equivalents.getByText("These medicines contain the same active ingredient")).toBeVisible();
  await expect(equivalents.getByRole("link")).toHaveCount(13);

  const nearby = page.getByRole("region", { name: "Available near you" });
  await expect(nearby.getByText("Simulated availability, for the demo.")).toBeVisible();
  await expect(nearby.getByRole("link", { name: /^Call/ }).first()).toHaveAttribute("href", /^tel:/);

  await expect(page.locator(".leaflet-container")).toBeVisible();
  await expect(page.locator(".marker-pin--stock").first()).toBeVisible();
  const legend = page.getByRole("list", { name: "Map legend" });
  for (const label of ["In stock", "Out of stock", "No information"]) await expect(legend).toContainText(label);
});

test("a patient can ask for an email alert", async ({ page }, testInfo) => {
  // One email per device: a second alert on the same medicine is refused
  const email = `patient.${testInfo.project.name}@example.com`;
  await page.goto(`/medicament/${GLUCOPHAGE_850}`);
  const alert = page.getByRole("region", { name: "Tell me when it’s back" });
  await alert.getByLabel("Your email").fill(email);
  await alert.getByRole("button", { name: "Notify me" }).click();
  await expect(alert.getByRole("status")).toContainText("Your alert is saved");
  await expect(alert.getByRole("status")).toContainText(email);
});

test("a modified-release medicine without equivalent says so", async ({ page }) => {
  await page.goto("/");
  await search(page, "diamicron");
  await page.getByRole("option", { name: /Diamicron 60 mg/ }).click();

  const equivalents = page.getByRole("region", { name: "Equivalents registered in Algeria" });
  await expect(equivalents.getByText("No equivalent registered")).toBeVisible();
  await expect(equivalents.getByText("Talk to your doctor")).toBeVisible();
});

test("an unknown medicine shows a clear message", async ({ page }) => {
  await page.goto("/medicament/000000000000");
  await expect(page.getByRole("heading", { name: "Medicine not found" })).toBeVisible();
});

test("the map still works after the browser Back button", async ({ page }) => {
  const crashes: string[] = [];
  page.on("pageerror", (error) => crashes.push(error.message));
  await page.goto(`/medicament/${GLUCOPHAGE_850}`);
  await expect(page.locator(".marker-pin--stock").first()).toBeVisible();

  await page.getByRole("region", { name: "Equivalents registered in Algeria" }).getByRole("link").first().click();
  await expect(page).not.toHaveURL(new RegExp(GLUCOPHAGE_850));
  await expect(page.locator(".leaflet-container:visible")).toBeVisible();

  await page.goBack();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Glucophage 850");
  await expect(page.locator(".marker-pin--stock:visible").first()).toBeVisible();
  await expect(page.getByText("Something went wrong")).toHaveCount(0);
  expect(crashes).toEqual([]);
});

test("far from Oran, the position falls back to Oran city centre", async ({ page, context }) => {
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation({ latitude: 36.7538, longitude: 3.0588 }); // Algiers
  await page.goto(`/medicament/${GLUCOPHAGE_850}`);
  await page.getByRole("button", { name: /my position/ }).click();

  await expect(page.getByText("You are far from Oran.")).toBeVisible();
  await expect(page.getByText(/Pharmacies around/).first()).toContainText("Oran city centre");
  await expect(page.locator(".marker-pin--stock").first()).toBeVisible();
});
