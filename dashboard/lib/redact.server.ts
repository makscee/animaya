import "server-only";

/**
 * Regex-based secret scrubber for error messages returned to the client.
 * Defense-in-depth: each route handler's catch arm should call this before
 * echoing any exception string.
 *
 * Patterns covered:
 *   - Telegram bot tokens: `<8-10 digits>:<35 chars base64url-ish>`
 *   - Claude / Anthropic OAuth tokens: `sk-ant-oat01-...` or `sk-<long>`
 *   - Long hex blobs (≥32 chars) — catches raw HMAC/hash leaks
 */
const TELEGRAM_TOKEN_RE = /\b\d{8,10}:[A-Za-z0-9_-]{35,}\b/g;
const CLAUDE_OAUTH_RE = /\bsk-(?:ant-oat01-)?[A-Za-z0-9_-]{20,}\b/g;
const LONG_HEX_RE = /\b[a-f0-9]{32,}\b/g;

export function sanitizeErrorMessage(s: string): string {
  return s
    .replace(TELEGRAM_TOKEN_RE, "[REDACTED_TG_TOKEN]")
    .replace(CLAUDE_OAUTH_RE, "[REDACTED_OAUTH]")
    .replace(LONG_HEX_RE, "[REDACTED_HEX]");
}

/**
 * Deep-walks a value and replaces the value of any key whose name looks
 * like a secret with `"[REDACTED]"`. Defense-in-depth mirror of the
 * Python-side `_scrub_mapping` in `bot/engine/modules_rpc.py`.
 *
 * CR-02 (Phase 13 review): Zod's `z.record(z.string(), z.unknown())` in
 * `ModuleConfigSchema` accepts arbitrary keys, so the schema alone does
 * NOT strip fields like `google_api_key` or `auth.token`. This helper is
 * applied in response handlers for list/detail module DTOs.
 */
const SECRET_KEY_RE = /token|secret|api_key|apikey|password|credential|oauth/i;

export function deepRedact<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.map((v) => deepRedact(v)) as unknown as T;
  }
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      if (SECRET_KEY_RE.test(k)) {
        out[k] = "[REDACTED]";
      } else if (v && typeof v === "object") {
        out[k] = deepRedact(v);
      } else {
        out[k] = v;
      }
    }
    return out as unknown as T;
  }
  return value;
}
