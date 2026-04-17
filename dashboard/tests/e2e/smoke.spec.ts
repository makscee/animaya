import { expect, test } from "@playwright/test";

/**
 * Wave 1 smoke: server boots, "/" responds with a non-500 status.
 * Downstream plans replace this with DASH-01..04 coverage.
 */
test("home route responds without 5xx", async ({ page }) => {
  const response = await page.goto("/");
  expect(response, "page.goto returned no response").not.toBeNull();
  const status = response!.status();
  expect(status, `unexpected status ${status}`).toBeLessThan(500);
});
