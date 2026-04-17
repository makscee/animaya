import { expect, test } from "@playwright/test";

/**
 * D-06: DASHBOARD_TOKEN header bypasses the session gate so scripted
 * operations can reach the dashboard without completing the Telegram
 * widget flow. Playwright webServer exposes `DASHBOARD_TOKEN=test-dash-token`.
 */

test("valid DASHBOARD_TOKEN header grants access without session", async ({
  browser,
}) => {
  const ctx = await browser.newContext({
    extraHTTPHeaders: { "x-dashboard-token": "test-dash-token" },
  });
  const page = await ctx.newPage();
  const res = await page.goto("/");
  expect(res?.status()).toBeLessThan(400);
  await expect(page).not.toHaveURL(/\/login$/);
  await ctx.close();
});

test("invalid DASHBOARD_TOKEN falls through to /login", async ({ browser }) => {
  const ctx = await browser.newContext({
    extraHTTPHeaders: { "x-dashboard-token": "nope" },
  });
  const page = await ctx.newPage();
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await ctx.close();
});

test("DASHBOARD_TOKEN via query param also works", async ({ browser }) => {
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  const res = await page.goto("/?token=test-dash-token");
  expect(res?.status()).toBeLessThan(400);
  await expect(page).not.toHaveURL(/\/login$/);
  await ctx.close();
});
