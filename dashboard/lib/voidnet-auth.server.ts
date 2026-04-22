// This module runs in the Next.js Edge runtime (Next middleware). It cannot
// import `server-only`, because `server-only` throws at module eval. The
// `.server` suffix is used here only to mark it as non-client-bundled;
// disable the Next lint rule that assumes Node runtime semantics.
/* eslint-disable server-only/server-only */
import { edgeConstantTimeEqual } from "@/lib/ct-compare";

/**
 * Pure Edge-safe voidnet header verifier. Runs inside Next.js middleware
 * (Edge runtime) so this module MUST NOT import `server-only` or
 * `node:crypto`. All HMAC work goes through WebCrypto (`crypto.subtle`).
 *
 * Contract (locked, see 14-SPEC.md):
 *   Canonical signing input: `${userId}|${handle}|${telegramId}|${timestamp}`
 *   Algorithm: HMAC-SHA256 → lowercase hex (64 chars)
 *   Replay window: |now - ts| <= 60s
 *   Check order: schema → replay → HMAC → owner
 */

const enc = new TextEncoder();
const HANDLE_RE = /^[a-z][a-z0-9-]+$/;
const I64_RE = /^-?\d+$/;
const HEX64_RE = /^[0-9a-f]{64}$/;
const REPLAY_WINDOW_SEC = 60;

export type VoidnetClaims = {
  userId: string;
  handle: string;
  telegramId: string;
  timestamp: number;
};

export type VerifyResult =
  | { ok: true; claims: VoidnetClaims }
  | { ok: false; status: 401 | 403; error: string; code: string };

function fail(status: 401 | 403, error: string, code: string): VerifyResult {
  return { ok: false, status, error, code };
}

async function hmacSha256Hex(secret: string, message: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(message));
  return Array.from(new Uint8Array(sig), (b) =>
    b.toString(16).padStart(2, "0"),
  ).join("");
}

export async function verifyVoidnetHeaders(
  h: Headers,
  secret: string,
  ownerTelegramId: string | undefined,
): Promise<VerifyResult> {
  const userId = h.get("x-voidnet-user-id") ?? "";
  const handle = h.get("x-voidnet-handle") ?? "";
  const telegramId = h.get("x-voidnet-telegram-id") ?? "";
  const tsStr = h.get("x-voidnet-timestamp") ?? "";
  const sig = h.get("x-voidnet-signature") ?? "";

  // Schema checks (cheapest first).
  if (!I64_RE.test(userId)) return fail(401, "bad user_id", "VOIDNET_SCHEMA");
  if (
    handle.length < 3 ||
    handle.length > 32 ||
    !HANDLE_RE.test(handle)
  )
    return fail(401, "bad handle", "VOIDNET_SCHEMA");
  if (!I64_RE.test(telegramId))
    return fail(401, "bad telegram_id", "VOIDNET_SCHEMA");
  if (!/^\d+$/.test(tsStr))
    return fail(401, "bad timestamp", "VOIDNET_SCHEMA");
  if (!HEX64_RE.test(sig))
    return fail(401, "bad signature", "VOIDNET_SCHEMA");

  // Replay window (±60s).
  const ts = Number(tsStr);
  const now = Math.floor(Date.now() / 1000);
  if (Math.abs(now - ts) > REPLAY_WINDOW_SEC)
    return fail(401, "timestamp out of window", "VOIDNET_STALE");

  // HMAC verify (constant-time hex compare).
  const expected = await hmacSha256Hex(
    secret,
    `${userId}|${handle}|${telegramId}|${ts}`,
  );
  if (!edgeConstantTimeEqual(expected, sig))
    return fail(401, "invalid signature", "VOIDNET_SIG_INVALID");

  // Owner invariant — only meaningful after sig verify.
  if (!ownerTelegramId || ownerTelegramId !== telegramId)
    return fail(403, "owner mismatch", "VOIDNET_OWNER_MISMATCH");

  return {
    ok: true,
    claims: { userId, handle, telegramId, timestamp: ts },
  };
}
