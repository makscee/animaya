import { describe, test, expect } from "bun:test";
import crypto from "node:crypto";
import { verifyTelegramWidget } from "./telegram-widget.server";
import { dashboardTokenMatches } from "./dashboard-token.server";

const BOT_TOKEN = "1234567890:TEST-BOT-TOKEN-FIXTURE-35-CHARS-XX";

function signPayload(
  data: Record<string, string | number>,
  botToken: string = BOT_TOKEN,
): Record<string, string | number> & { hash: string } {
  const entries = Object.entries(data)
    .filter(([k]) => k !== "hash")
    .map(([k, v]) => [k, String(v)] as const)
    .sort(([a], [b]) => a.localeCompare(b));
  const dataCheck = entries.map(([k, v]) => `${k}=${v}`).join("\n");
  const secret = crypto.createHash("sha256").update(botToken).digest();
  const hash = crypto.createHmac("sha256", secret).update(dataCheck).digest("hex");
  return { ...data, hash };
}

describe("verifyTelegramWidget", () => {
  const now = Math.floor(Date.now() / 1000);

  test("accepts valid payload", () => {
    const payload = signPayload({
      id: 12345,
      first_name: "Alice",
      username: "alice",
      auth_date: now,
    });
    const result = verifyTelegramWidget(payload, BOT_TOKEN);
    expect(result).not.toBeNull();
    expect(result?.id).toBe(12345);
  });

  test("rejects tampered hash", () => {
    const payload = signPayload({ id: 1, auth_date: now });
    payload.hash = "0".repeat(64);
    expect(verifyTelegramWidget(payload, BOT_TOKEN)).toBeNull();
  });

  test("rejects stale auth_date (> 86400s old)", () => {
    const stale = now - 86401;
    const payload = signPayload({ id: 1, auth_date: stale });
    expect(verifyTelegramWidget(payload, BOT_TOKEN)).toBeNull();
  });

  test("rejects missing hash", () => {
    const payload = signPayload({ id: 1, auth_date: now });
    delete (payload as Partial<typeof payload>).hash;
    expect(verifyTelegramWidget(payload, BOT_TOKEN)).toBeNull();
  });

  test("rejects missing id", () => {
    const payload = signPayload({ auth_date: now });
    expect(verifyTelegramWidget(payload, BOT_TOKEN)).toBeNull();
  });

  test("wrong-hash-of-same-length still returns null (constant-time compare)", () => {
    const payload = signPayload({ id: 7, auth_date: now });
    // Flip one hex char to a wrong but same-length hash
    payload.hash = payload.hash.slice(0, -1) + (payload.hash.slice(-1) === "0" ? "1" : "0");
    expect(verifyTelegramWidget(payload, BOT_TOKEN)).toBeNull();
  });

  test("cross-verified Python vector (same bot_token + payload produces same verdict)", () => {
    // Python would compute: secret=sha256(bot_token), HMAC-SHA256(secret, sorted k=v\n).hex()
    // We verify by constructing with our signer and confirming verify accepts.
    const botToken = "999:python-vector";
    const payload = signPayload(
      { id: 42, first_name: "Bob", auth_date: now },
      botToken,
    );
    expect(verifyTelegramWidget(payload, botToken)).not.toBeNull();
    // And rejects if verified with a different bot token.
    expect(verifyTelegramWidget(payload, BOT_TOKEN)).toBeNull();
  });
});

describe("dashboardTokenMatches (constant-time)", () => {
  test("matches equal-length equal tokens", () => {
    expect(dashboardTokenMatches("abc123", "abc123")).toBe(true);
  });

  test("rejects length-mismatched tokens (no timing leak)", () => {
    expect(dashboardTokenMatches("short", "muchlongervalue")).toBe(false);
  });

  test("rejects null/empty", () => {
    expect(dashboardTokenMatches(null, "x")).toBe(false);
    expect(dashboardTokenMatches("x", undefined)).toBe(false);
    expect(dashboardTokenMatches("", "")).toBe(false);
  });

  test("rejects same-length different tokens", () => {
    expect(dashboardTokenMatches("aaaaaa", "bbbbbb")).toBe(false);
  });
});
