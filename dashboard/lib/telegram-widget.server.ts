import "server-only";
import crypto from "node:crypto";

/**
 * Telegram Login Widget payload shape.
 * `hash` is the HMAC-SHA256 signature over the sorted `key=value\n` data-check-string,
 * keyed by SHA-256(bot_token). See https://core.telegram.org/widgets/login.
 */
export type TelegramPayload = {
  id: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
  hash: string;
  [k: string]: unknown;
};

/**
 * Verify a Telegram Login Widget payload.
 *
 * Canonical algorithm (matches the Python reference in bot/dashboard/auth.py
 * and Telegram's public widget spec):
 *   1. Remove `hash` from the payload.
 *   2. Build data-check-string = sorted `key=value` joined by `\n`.
 *   3. secret = SHA-256(bot_token)   (raw 32-byte digest)
 *   4. expected = HMAC-SHA256(secret, data-check-string)  → hex
 *   5. Constant-time compare with provided `hash`.
 *   6. Reject if `auth_date` is older than 86400s (1 day).
 *
 * Returns the typed payload on success, or `null` on any failure (fail-closed).
 */
export function verifyTelegramWidget(
  raw: unknown,
  botToken: string,
): TelegramPayload | null {
  if (!raw || typeof raw !== "object") return null;
  const obj = raw as Record<string, unknown>;

  const hash = obj.hash;
  if (typeof hash !== "string" || hash.length === 0) return null;

  const authDate = Number(obj.auth_date);
  if (!Number.isFinite(authDate)) return null;
  if (Math.floor(Date.now() / 1000) - authDate > 86400) return null;

  if (typeof obj.id !== "number" && typeof obj.id !== "string") return null;

  const entries = Object.entries(obj)
    .filter(([k]) => k !== "hash")
    .map(([k, v]) => [k, String(v)] as const)
    .sort(([a], [b]) => a.localeCompare(b));
  const dataCheckString = entries.map(([k, v]) => `${k}=${v}`).join("\n");

  const secret = crypto.createHash("sha256").update(botToken).digest();
  const expectedHex = crypto
    .createHmac("sha256", secret)
    .update(dataCheckString)
    .digest("hex");

  let a: Buffer;
  let b: Buffer;
  try {
    a = Buffer.from(expectedHex, "hex");
    b = Buffer.from(hash, "hex");
  } catch {
    return null;
  }
  if (a.length === 0 || a.length !== b.length) return null;
  if (!crypto.timingSafeEqual(a, b)) return null;

  const idNum = typeof obj.id === "number" ? obj.id : Number(obj.id);
  if (!Number.isFinite(idNum)) return null;

  return { ...(obj as object), id: idNum, auth_date: authDate, hash } as TelegramPayload;
}
