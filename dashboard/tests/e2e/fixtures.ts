/**
 * Shared Playwright fixtures for Animaya dashboard E2E tests.
 *
 * These helpers establish the test-surface contract for downstream plans
 * (13-02 Telegram HMAC auth, 13-03 SEC-01/02 route handlers, 13-04 DASH-01..04
 * full UI E2E). Wave 1 keeps them minimal but fully exported — signatures are
 * stable and implementations land progressively in subsequent plans.
 */
import { createHmac } from "node:crypto";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { Page, APIRequestContext } from "@playwright/test";

/**
 * Build a Telegram Login Widget payload with a correctly-HMAC'd `hash` field.
 *
 * Telegram's auth spec: data_check_string = sorted key=value pairs joined by
 * \n; secret = SHA256(bot_token); hash = HMAC-SHA256(secret, data_check_string).
 *
 * Bot token defaults to "0:dummy" — matches the Playwright webServer env.
 */
export interface TelegramWidgetPayload {
  id: number;
  first_name: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
  hash: string;
}

export function mockTelegramWidgetPayload(
  overrides: Partial<Omit<TelegramWidgetPayload, "hash">> & { botToken?: string } = {},
): TelegramWidgetPayload {
  const botToken = overrides.botToken ?? "0:dummy";
  const base = {
    id: overrides.id ?? 111111,
    first_name: overrides.first_name ?? "TestOwner",
    username: overrides.username,
    photo_url: overrides.photo_url,
    auth_date: overrides.auth_date ?? Math.floor(Date.now() / 1000),
  };
  const dataCheck = Object.entries(base)
    .filter(([, v]) => v !== undefined)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${k}=${v}`)
    .join("\n");
  const secret = createHmac("sha256", "WebAppData").update(botToken).digest();
  // Telegram Login Widget uses SHA256(bot_token) as secret, not HMAC:
  const shaSecret = require("node:crypto").createHash("sha256").update(botToken).digest();
  const hash = createHmac("sha256", shaSecret).update(dataCheck).digest("hex");
  // `secret` intentionally computed above to document the WebApp variant; not used here.
  void secret;
  return { ...base, hash };
}

/**
 * Attach the DASHBOARD_TOKEN header to a Playwright request context or page.
 * Use when the test needs to bypass next-auth session and authenticate via
 * the scripted-ops bearer token path (D-06).
 */
export function signedInRequest(pageOrRequest: Page | APIRequestContext): {
  headers: Record<string, string>;
} {
  void pageOrRequest;
  return {
    headers: {
      "x-dashboard-token": process.env.DASHBOARD_TOKEN ?? "test-dash-token",
    },
  };
}

/**
 * Write a temporary OWNER.md file with the given Telegram owner id and return
 * its absolute path. Consumers set ANIMAYA_DATA_PATH (or the production var)
 * to the containing directory before the server boots.
 */
export function withOwnerFile(ownerId: number | string): { dir: string; path: string } {
  const dir = mkdtempSync(join(tmpdir(), "animaya-owner-"));
  const path = join(dir, "OWNER.md");
  writeFileSync(
    path,
    `# Owner\n\n- telegram_id: ${ownerId}\n- created: ${new Date().toISOString()}\n`,
    "utf8",
  );
  return { dir, path };
}
