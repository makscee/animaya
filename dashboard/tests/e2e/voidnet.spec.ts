import { expect, test } from "@playwright/test";
import { voidnetHeaders } from "./_voidnet-helpers";

/**
 * Phase 14 — VoidNet integration auth E2E spec.
 *
 * Wave 0 scaffold: most of these tests are RED until Plan 03 wires the voidnet
 * branch into `dashboard/middleware.ts`. They lock the error contract so Plan
 * 03's middleware cannot drift from the spec:
 *   - 401 JSON {error, code: VOIDNET_SIG_INVALID | VOIDNET_STALE | VOIDNET_SCHEMA}
 *   - 403 JSON {error, code: VOIDNET_OWNER_MISMATCH}
 *   - Absent headers → Telegram login flow unchanged
 *   - GET /api/integration/v1/meta auth-gated and shape-locked
 */

test("valid voidnet headers grant access without Telegram widget redirect", async ({
  browser,
}) => {
  const ctx = await browser.newContext({
    extraHTTPHeaders: voidnetHeaders(),
  });
  const page = await ctx.newPage();
  const res = await page.goto("/");
  expect(res?.status()).toBeLessThan(400);
  await expect(page).not.toHaveURL(/\/login$/);
  await ctx.close();
});

test("tampered signature → 401 JSON {error, code: VOIDNET_SIG_INVALID}", async ({
  request,
}) => {
  const res = await request.get("/", { headers: voidnetHeaders({ tamper: true }) });
  expect(res.status()).toBe(401);
  const body = await res.json();
  expect(body).toMatchObject({ code: "VOIDNET_SIG_INVALID" });
  expect(typeof body.error).toBe("string");
});

test("stale timestamp (-90s) → 401 JSON {error, code: VOIDNET_STALE}", async ({
  request,
}) => {
  const res = await request.get("/", { headers: voidnetHeaders({ offset: -90 }) });
  expect(res.status()).toBe(401);
  const body = await res.json();
  expect(body).toMatchObject({ code: "VOIDNET_STALE" });
  expect(typeof body.error).toBe("string");
});

test("owner mismatch (telegramId=999999) → 403 JSON {error, code: VOIDNET_OWNER_MISMATCH}", async ({
  request,
}) => {
  const res = await request.get("/", {
    headers: voidnetHeaders({ telegramId: "999999" }),
  });
  expect(res.status()).toBe(403);
  const body = await res.json();
  expect(body).toMatchObject({ code: "VOIDNET_OWNER_MISMATCH" });
  expect(typeof body.error).toBe("string");
});

test("no voidnet headers → Telegram flow unchanged (redirect to /login)", async ({
  browser,
}) => {
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await ctx.close();
});

test("GET /api/integration/v1/meta with valid sig → 200 {version, supported_auth_modes, dashboard_port}", async ({
  request,
}) => {
  const res = await request.get("/api/integration/v1/meta", {
    headers: voidnetHeaders(),
  });
  expect(res.status()).toBe(200);
  const body = await res.json();
  expect(typeof body.version).toBe("string");
  expect(body.supported_auth_modes).toEqual(["telegram", "voidnet"]);
  expect(body.dashboard_port).toBe(8090);
});

test("GET /api/integration/v1/meta without sig → 401", async ({ request }) => {
  const res = await request.get("/api/integration/v1/meta");
  expect(res.status()).toBe(401);
});
