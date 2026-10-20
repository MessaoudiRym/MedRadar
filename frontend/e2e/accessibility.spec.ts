import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { GLUCOPHAGE_850 } from "./config";

// Automatic accessibility check (WCAG 2.1 A and AA rules) on the public pages.
// It does not replace a manual check, but catches missing labels, contrast
// problems and invalid ARIA.
const PAGES = [
  { name: "home", path: "/" },
  { name: "medicine", path: `/medicament/${GLUCOPHAGE_850}`, ready: ".marker-pin--stock" },
  { name: "login", path: "/pharmacien/connexion" },
  { name: "registration", path: "/pharmacien/inscription" },
  { name: "privacy", path: "/confidentialite" },
];

for (const p of PAGES) {
  test(`no serious accessibility problem: ${p.name}`, async ({ page }) => {
    await page.goto(p.path);
    if (p.ready) await expect(page.locator(p.ready).first()).toBeVisible();
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      // Map tiles are images drawn by OpenStreetMap, not content
      .exclude(".leaflet-tile-pane")
      .analyze();
    const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious.map((v) => `${v.id}: ${v.help} (${v.nodes.length})`)).toEqual([]);
  });
}
