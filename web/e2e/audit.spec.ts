import { expect, test } from "@playwright/test";
import { mockApi } from "./fixtures";

/**
 * Audit screen e2e: a clinic is selected by default, the week grid renders, a
 * block is moved by keyboard (the accessible drag alternative), and the
 * before -> after delta text appears. A drag move is also attempted.
 */

test.beforeEach(async ({ page }) => {
  await mockApi(page);
  await page.goto("/#/audit");
});

test("pick a clinic, see the grid, move a block by keyboard, see the delta", async ({
  page,
}) => {
  // The clinic picker is populated from /clinics.
  const clinicSelect = page.getByLabel("Clinic");
  await expect(clinicSelect).toBeVisible();
  await expect(clinicSelect.locator("option").first()).toHaveText(
    /Riverside Community Health/,
  );

  // The week grid renders as a table with hour cells.
  const grid = page.locator("table.weekgrid");
  await expect(grid).toBeVisible();

  // Monday 8 am cell exists and shows a percentage.
  const fromCell = page.locator("#cell-mon-08");
  await expect(fromCell).toBeVisible();
  await expect(fromCell).toHaveText(/\d{1,3}%/);

  // Keyboard move: focus the cell, Enter picks up, ArrowDown moves one hour,
  // Enter drops. (component: arrow keys move within the day column.)
  await fromCell.focus();
  await page.keyboard.press("Enter"); // pick up
  await page.keyboard.press("ArrowDown"); // mon-08 -> mon-09 row
  await page.keyboard.press("Enter"); // drop on 9 am

  // The before/after panel appears with a "pts" delta.
  const beforeAfter = page.locator(".beforeafter");
  await expect(beforeAfter).toBeVisible();
  await expect(beforeAfter).toContainText("Before");
  await expect(beforeAfter).toContainText("After");
  await expect(beforeAfter.locator(".delta")).toContainText(/[+-]?\d+ pts/);
});

test("move a block by drag-and-drop shows the delta", async ({ page }) => {
  await expect(page.locator("table.weekgrid")).toBeVisible();

  const from = page.locator("#cell-tue-07");
  const to = page.locator("#cell-tue-10");
  await expect(from).toBeVisible();
  await expect(to).toBeVisible();

  // Playwright's dragTo issues the HTML5 drag sequence the component listens for
  // (dragstart on source, dragover + drop on target in the same column).
  await from.dragTo(to);

  const beforeAfter = page.locator(".beforeafter");
  await expect(beforeAfter).toBeVisible();
  await expect(beforeAfter.locator(".delta")).toContainText(/[+-]?\d+ pts/);
});
