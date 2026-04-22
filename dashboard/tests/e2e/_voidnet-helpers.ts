import crypto from "node:crypto";

/**
 * Voidnet HMAC signer helper for Playwright E2E tests.
 *
 * Must mirror the canonical signature format locked in 14-CONTEXT.md:
 *   hmac_sha256(SECRET, `${userId}|${handle}|${telegramId}|${timestamp}`)
 *
 * SECRET and OWNER must match values injected into playwright.config.ts
 * `webServer.env` so the dashboard process sees the same secret and owner id.
 */

export const SECRET = "test-voidnet-secret";
// Must equal OWNER_TELEGRAM_ID in playwright.config.ts webServer.env.
export const OWNER = "111111";

export function voidnetHeaders(
  opts: { telegramId?: string; tamper?: boolean; offset?: number } = {},
): Record<string, string> {
  const telegramId = opts.telegramId ?? OWNER;
  const userId = "42";
  const handle = "testuser";
  const ts = Math.floor(Date.now() / 1000) + (opts.offset ?? 0);
  const msg = `${userId}|${handle}|${telegramId}|${ts}`;
  let sig = crypto.createHmac("sha256", SECRET).update(msg).digest("hex");
  if (opts.tamper) {
    sig = sig.slice(0, -1) + (sig.slice(-1) === "0" ? "1" : "0");
  }
  return {
    "x-voidnet-user-id": userId,
    "x-voidnet-handle": handle,
    "x-voidnet-telegram-id": telegramId,
    "x-voidnet-timestamp": String(ts),
    "x-voidnet-signature": sig,
  };
}
