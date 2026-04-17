import { expect, test } from "@playwright/test";

/**
 * D-05: Telegram Login Widget is the only interactive sign-in path.
 * D-07: only OWNER_TELEGRAM_ID (111111 in Playwright env) is allowed;
 * other Telegram IDs land on /403.
 *
 * Note: Plan 13-03 (route handlers) is not merged on this branch, so we
 * exercise the middleware gate (unauth redirect) and the login page
 * surface. End-to-end HMAC Credentials POST is covered in lib-level
 * tests (13-02) — Task 3 asserts the visible UI contract.
 */

test("unauth visit to / redirects to /login", async ({ page }) => {
  const res = await page.goto("/");
  expect(res?.status()).toBeLessThan(400);
  await expect(page).toHaveURL(/\/login$/);
});

test("/login renders the Telegram Widget mount", async ({ page }) => {
  // Widget only mounts when NEXT_PUBLIC_TELEGRAM_BOT_USERNAME is set.
  // In webServer env it's unset, so we assert the informative fallback.
  await page.goto("/login");
  const html = await page.content();
  expect(
    html.includes("NEXT_PUBLIC_TELEGRAM_BOT_USERNAME") ||
      html.includes("telegram-widget"),
  ).toBeTruthy();
});

test("/403 page renders an owner-rejection message", async ({ page }) => {
  await page.goto("/403");
  await expect(page.locator("h1")).toContainText(/403/);
  await expect(page.locator("body")).toContainText(/not the Animaya owner|Not Authorized/i);
});
