import { describe, test, expect } from "bun:test";
import crypto from "node:crypto";
import { verifyVoidnetHeaders } from "./voidnet-auth.server";

// Wave 0 RED: `./voidnet-auth.server` does not exist yet — Plan 02 implements it.
// These tests lock canonical signature format, ±60s replay window, error codes,
// and owner invariant so Plan 02's verifier cannot drift.

const SECRET = "test-voidnet-secret";
const OWNER = "111111";

type SignInput = {
  userId: string;
  handle: string;
  telegramId: string;
  timestamp: number;
};

function signHeaders(input: SignInput): Headers {
  const msg = `${input.userId}|${input.handle}|${input.telegramId}|${input.timestamp}`;
  const hash = crypto.createHmac("sha256", SECRET).update(msg).digest("hex");
  return new Headers({
    "x-voidnet-user-id": input.userId,
    "x-voidnet-handle": input.handle,
    "x-voidnet-telegram-id": input.telegramId,
    "x-voidnet-timestamp": String(input.timestamp),
    "x-voidnet-signature": hash,
  });
}

function now(): number {
  return Math.floor(Date.now() / 1000);
}

describe("verifyVoidnetHeaders", () => {
  test("accepts valid headers (claims match, ok:true)", async () => {
    const ts = now();
    const h = signHeaders({
      userId: "42",
      handle: "testuser",
      telegramId: OWNER,
      timestamp: ts,
    });
    const result = await verifyVoidnetHeaders(h, SECRET, OWNER);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.claims.userId).toBe("42");
      expect(result.claims.handle).toBe("testuser");
      expect(result.claims.telegramId).toBe(OWNER);
      expect(result.claims.timestamp).toBe(ts);
    }
  });

  test("rejects tampered signature → VOIDNET_SIG_INVALID, status 401", async () => {
    const ts = now();
    const h = signHeaders({
      userId: "42",
      handle: "testuser",
      telegramId: OWNER,
      timestamp: ts,
    });
    const sig = h.get("x-voidnet-signature")!;
    const flipped = sig.slice(0, -1) + (sig.slice(-1) === "0" ? "1" : "0");
    h.set("x-voidnet-signature", flipped);
    const result = await verifyVoidnetHeaders(h, SECRET, OWNER);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.code).toBe("VOIDNET_SIG_INVALID");
      expect(result.status).toBe(401);
    }
  });

  test("rejects bad handle too short (2 chars) → VOIDNET_SCHEMA", async () => {
    const h = signHeaders({
      userId: "42",
      handle: "ab",
      telegramId: OWNER,
      timestamp: now(),
    });
    const result = await verifyVoidnetHeaders(h, SECRET, OWNER);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.code).toBe("VOIDNET_SCHEMA");
  });

  test("rejects bad handle bad chars (uppercase) → VOIDNET_SCHEMA", async () => {
    const h = signHeaders({
      userId: "42",
      handle: "TestUser",
      telegramId: OWNER,
      timestamp: now(),
    });
    const result = await verifyVoidnetHeaders(h, SECRET, OWNER);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.code).toBe("VOIDNET_SCHEMA");
  });

  test("rejects non-numeric user_id → VOIDNET_SCHEMA", async () => {
    const h = signHeaders({
      userId: "abc",
      handle: "testuser",
      telegramId: OWNER,
      timestamp: now(),
    });
    const result = await verifyVoidnetHeaders(h, SECRET, OWNER);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.code).toBe("VOIDNET_SCHEMA");
  });

  test("rejects non-numeric telegram_id → VOIDNET_SCHEMA", async () => {
    const h = signHeaders({
      userId: "42",
      handle: "testuser",
      telegramId: "notanid",
      timestamp: now(),
    });
    const result = await verifyVoidnetHeaders(h, SECRET, OWNER);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.code).toBe("VOIDNET_SCHEMA");
  });

  test("rejects non-numeric timestamp → VOIDNET_SCHEMA", async () => {
    const h = new Headers({
      "x-voidnet-user-id": "42",
      "x-voidnet-handle": "testuser",
      "x-voidnet-telegram-id": OWNER,
      "x-voidnet-timestamp": "notatime",
      "x-voidnet-signature": "a".repeat(64),
    });
    const result = await verifyVoidnetHeaders(h, SECRET, OWNER);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.code).toBe("VOIDNET_SCHEMA");
  });

  test("rejects signature not 64-hex → VOIDNET_SCHEMA", async () => {
    const h = new Headers({
      "x-voidnet-user-id": "42",
      "x-voidnet-handle": "testuser",
      "x-voidnet-telegram-id": OWNER,
      "x-voidnet-timestamp": String(now()),
      "x-voidnet-signature": "xyz",
    });
    const result = await verifyVoidnetHeaders(h, SECRET, OWNER);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.code).toBe("VOIDNET_SCHEMA");
  });

  test("rejects timestamp 61s in past → VOIDNET_STALE", async () => {
    const h = signHeaders({
      userId: "42",
      handle: "testuser",
      telegramId: OWNER,
      timestamp: now() - 61,
    });
    const result = await verifyVoidnetHeaders(h, SECRET, OWNER);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.code).toBe("VOIDNET_STALE");
      expect(result.status).toBe(401);
    }
  });

  test("rejects timestamp 61s in future → VOIDNET_STALE", async () => {
    const h = signHeaders({
      userId: "42",
      handle: "testuser",
      telegramId: OWNER,
      timestamp: now() + 61,
    });
    const result = await verifyVoidnetHeaders(h, SECRET, OWNER);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.code).toBe("VOIDNET_STALE");
  });

  test("accepts timestamp -59s → ok:true", async () => {
    const h = signHeaders({
      userId: "42",
      handle: "testuser",
      telegramId: OWNER,
      timestamp: now() - 59,
    });
    const result = await verifyVoidnetHeaders(h, SECRET, OWNER);
    expect(result.ok).toBe(true);
  });

  test("accepts timestamp +59s → ok:true", async () => {
    const h = signHeaders({
      userId: "42",
      handle: "testuser",
      telegramId: OWNER,
      timestamp: now() + 59,
    });
    const result = await verifyVoidnetHeaders(h, SECRET, OWNER);
    expect(result.ok).toBe(true);
  });

  test("rejects owner mismatch (telegramId ≠ ownerTelegramId) → VOIDNET_OWNER_MISMATCH, status 403", async () => {
    // Sig is valid for telegramId=999999, but OWNER=111111 → 403.
    const h = signHeaders({
      userId: "42",
      handle: "testuser",
      telegramId: "999999",
      timestamp: now(),
    });
    const result = await verifyVoidnetHeaders(h, SECRET, OWNER);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.code).toBe("VOIDNET_OWNER_MISMATCH");
      expect(result.status).toBe(403);
    }
  });

  test("cross-verified vector: canonical message `{userId}|{handle}|{telegramId}|{timestamp}` locked", async () => {
    // Lock the canonical signature-input string. If Plan 02 reorders or changes
    // the separator, this test fails: the HMAC we compute here won't match
    // what the verifier computes.
    const userId = "42";
    const handle = "testuser";
    const telegramId = OWNER;
    const timestamp = now();
    const msg = `${userId}|${handle}|${telegramId}|${timestamp}`;
    const expectedHex = crypto.createHmac("sha256", SECRET).update(msg).digest("hex");
    expect(expectedHex).toMatch(/^[0-9a-f]{64}$/);

    const h = new Headers({
      "x-voidnet-user-id": userId,
      "x-voidnet-handle": handle,
      "x-voidnet-telegram-id": telegramId,
      "x-voidnet-timestamp": String(timestamp),
      "x-voidnet-signature": expectedHex,
    });
    const result = await verifyVoidnetHeaders(h, SECRET, OWNER);
    expect(result.ok).toBe(true);
  });
});
