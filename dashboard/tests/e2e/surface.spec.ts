import { expect, test, request } from "@playwright/test";

/**
 * D-01: loopback engine is NOT exposed on the public port. The Next.js
 * server on :8090 must not forward `/engine/*` to the FastAPI sidecar.
 * The sidecar is reachable directly on :8091 (loopback-only in prod).
 */
test("loopback engine is reachable on 8091 (direct)", async () => {
  const ctx = await request.newContext();
  const res = await ctx.get("http://127.0.0.1:8091/engine/status");
  expect(res.status()).toBe(200);
  const body = (await res.json()) as { ok: boolean };
  expect(body.ok).toBe(true);
  await ctx.dispose();
});

test("public port does not proxy /engine/*", async ({ request: req }) => {
  const res = await req.get("/engine/modules", { maxRedirects: 0 });
  // Middleware redirects unauth to /login (302/307), or Next returns 404 if
  // no matching route exists. The invariant is that the response is NOT the
  // engine's `modules` JSON (no passthrough to FastAPI on the public port).
  const body = await res.text().catch(() => "");
  expect(body).not.toContain("Whisper STT");
  expect([302, 307, 308, 404]).toContain(res.status());
});
