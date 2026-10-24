import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { mockApi } from "./fixtures";

/**
 * Accessibility scan of the Audit screen with axe-core. We run the WCAG A/AA
 * rule sets (2.0, 2.1, 2.2) and fail the test on any serious or critical
 * violation. Moderate/minor findings are reported but do not fail the build.
 */

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"];

async function scan(page: import("@playwright/test").Page) {
  return new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
}

function seriousOrCritical(
  violations: Awaited<ReturnType<typeof scan>>["violations"],
) {
  return violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  );
}

test("Audit screen has no serious/critical a11y violations", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/#/audit");

  // Wait for the grid so the scan covers the real content, not a spinner.
  await expect(page.locator("table.weekgrid")).toBeVisible();

  const results = await scan(page);
  const blocking = seriousOrCritical(results.violations);
  if (blocking.length > 0) {
    // Surface the rule ids + nodes so a failure is actionable.
    console.log(
      "a11y violations (serious/critical):\n" +
        JSON.stringify(
          blocking.map((v) => ({
            id: v.id,
            impact: v.impact,
            help: v.help,
            nodes: v.nodes.map((n) => n.target),
          })),
          null,
          2,
        ),
    );
  }
  expect(blocking).toEqual([]);
});

test("Audit screen with the Suggest panel open has no serious/critical violations", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/#/audit");
  await expect(page.locator("table.weekgrid")).toBeVisible();

  // Open suggestions so the panel's controls are scanned too.
  await page.getByRole("button", { name: /Suggest changes/i }).click();
  await expect(page.locator(".suggest-list, .notice, .status")).toBeVisible();

  const results = await scan(page);
  const blocking = seriousOrCritical(results.violations);
  if (blocking.length > 0) {
    console.log(
      "a11y violations (serious/critical):\n" +
        JSON.stringify(
          blocking.map((v) => ({
            id: v.id,
            impact: v.impact,
            help: v.help,
            nodes: v.nodes.map((n) => n.target),
          })),
          null,
          2,
        ),
    );
  }
  expect(blocking).toEqual([]);
});
