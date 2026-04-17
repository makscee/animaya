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
