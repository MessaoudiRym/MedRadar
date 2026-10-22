import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { GLUCOPHAGE_850 } from "./config";
import { readTestBox } from "./helpers";

// Automatic accessibility check (WCAG 2.1 A and AA rules) on the public pages.
// It does not replace a manual check, but catches missing labels, contrast
// problems and invalid ARIA.
const PAGES = [
  { name: "home", path: "/" },
  { name: "medicine", path: `/medicament/${GLUCOPHAGE_850}`, ready: ".marker-pin--stock" },
  { name: "login", path: "/pharmacien/connexion" },
  { name: "registration", path: "/pharmacien/inscription" },
  { name: "privacy", path: "/confidentialite" },
  { name: "photo confirmation", path: "/", before: readTestBox, ready: "text=Is this your medicine?" },
  { name: "search understood", path: "/recherche?q=%D8%BA%D9%84%D9%88%D9%83%D9%88%D9%81%D8%A7%D8%AC", ready: "text=we understood" },
  { name: "search refused", path: "/recherche?q=medicine%20for%20diabetes", ready: "text=does not choose" },
];

for (const p of PAGES) {
  test(`no serious accessibility problem: ${p.name}`, async ({ page }) => {
    await page.goto(p.path);
    if (p.before) await p.before(page);
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
