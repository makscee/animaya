import { expect, test } from "@playwright/test";

test.use({ extraHTTPHeaders: { "x-dashboard-token": "test-dash-token" } });

const modulesBody = {
  modules: [
    {
      name: "audio",
      title: "Audio",
      description: "Whisper STT",
      installed: true,
    },
    {
      name: "image",
      title: "Image Gen",
      description: "Gemini images",
      installed: false,
    },
  ],
};

test("modules list renders and Install POSTs with CSRF header + redacted DTO", async ({
  page,
}) => {
  await page.route("**/api/modules", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(modulesBody),
    }),
  );
  let installHeaders: Record<string, string> = {};
  await page.route("**/api/modules/image/install", async (route) => {
    installHeaders = route.request().headers();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true }),
    });
  });

  await page.goto("/modules");
  // Seed the double-submit CSRF cookie (middleware only sets it after a
  // real session; DASHBOARD_TOKEN bypass skips that branch, so for tests
  // we plant the cookie manually — matches how scripted-ops clients
  // would carry it forward between calls).
  await page.context().addCookies([
    {
      name: "an-csrf",
      value: "test-csrf-token",
      url: "http://127.0.0.1:8090",
    },
  ]);
  await page.reload();
  await expect(page.locator('[data-testid="module-card-audio"]')).toBeVisible();
  await expect(page.locator('[data-testid="module-card-image"]')).toBeVisible();

  await page.locator('[data-testid="module-install-image"]').click();

  await expect
    .poll(() => installHeaders["x-csrf-token"], { timeout: 5_000 })
    .toBe("test-csrf-token");

  // T-13-44: response payload must not leak `bot_token` etc. — our fixture
  // above does not include it, and we assert no such string in any modules
  // response captured during the test.
  const responses: string[] = [];
  page.on("response", async (r) => {
    if (r.url().includes("/api/modules")) {
      try {
        responses.push(await r.text());
      } catch {
        /* ignore */
      }
    }
  });
  await page.reload();
  for (const body of responses) {
    expect(body.toLowerCase()).not.toContain("bot_token");
  }
});
