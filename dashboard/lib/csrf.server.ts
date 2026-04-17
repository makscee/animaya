import "server-only";

import { randomBytes } from "node:crypto";
import type { NextRequest } from "next/server";

import {
  CSRF_COOKIE_NAME,
  CSRF_HEADER_NAME,
  EXPECTED_ORIGIN,
} from "./csrf.shared";

// Re-export the constants so existing server code can keep importing them
// from csrf.server. NEW callers from the client bundle MUST import from
// csrf.shared directly — `import "server-only"` above would otherwise
// poison the client build.
export { CSRF_COOKIE_NAME, CSRF_HEADER_NAME, EXPECTED_ORIGIN };

// --------------------------------------------------------------------------
// Token generation + cookie issuance
// --------------------------------------------------------------------------

/** Issue a cryptographically-random hex token (64 chars — 32 bytes entropy). */
export function generateCsrfToken(): string {
  return randomBytes(32).toString("hex");
}

/**
 * Build the Set-Cookie header value for the CSRF double-submit cookie.
 *
 * HttpOnly is INTENTIONALLY absent: client-side `document.cookie` reads the
 * value and mirrors it into the `x-csrf-token` request header. The cookie is
 * still safe because:
 *   1. SameSite=Strict blocks cross-site submission entirely in modern browsers.
 *   2. Secure ensures it never leaks over plaintext HTTP.
 *   3. The value is opaque (no session identity) — only co-submission with
 *      the matching header proves the browser possesses it.
 *
 * 8-hour Max-Age matches the typical interactive session length.
 */
export function csrfCookie(token: string): string {
  return `${CSRF_COOKIE_NAME}=${token}; Path=/; SameSite=Strict; Secure; Max-Age=28800`;
}

// --------------------------------------------------------------------------
// Verifier
// --------------------------------------------------------------------------

export class CsrfError extends Error {
  constructor(public readonly reason: string) {
    super(`csrf rejected: ${reason}`);
    this.name = "CsrfError";
  }
}

/**
 * Verify a mutation request passes CSRF double-submit.
 *
 * Defense-in-depth order:
 *   1. Origin header equality (when present).
 *   2. Cookie presence + minimum entropy.
 *   3. Header presence.
 *   4. Constant-time equality of cookie and header values.
 *
 * Throws `CsrfError` on any failure; Route Handlers translate to HTTP 403.
 */
export function verifyCsrf(req: NextRequest): void {
  // Step 1 — Origin (or Referer fallback) MUST be present and match
  // EXPECTED_ORIGIN. Modern browsers always emit Origin on mutation
  // requests; tolerating a missing value only widens the attack surface
  // to non-browser forgery. Referer is accepted as a fallback for
  // legacy clients/proxies that strip Origin, stripped to scheme+host
  // before comparison.
  const rawOrigin =
    req.headers.get("origin") ?? req.headers.get("referer");
  if (!rawOrigin) {
    throw new CsrfError("origin missing");
  }
  const originOnly = rawOrigin.replace(/^(https?:\/\/[^/]+).*$/, "$1");
  if (originOnly !== EXPECTED_ORIGIN) {
    throw new CsrfError("bad origin");
  }

  // Step 2 — Cookie presence + minimum entropy.
  const cookie = req.cookies.get(CSRF_COOKIE_NAME)?.value;
  if (!cookie) throw new CsrfError("cookie missing");
  if (cookie.length < 32) throw new CsrfError("cookie too short");

  // Step 3 — Header presence.
  const header = req.headers.get(CSRF_HEADER_NAME);
  if (!header) throw new CsrfError("header missing");

  // Step 4 — Constant-time equality (lengths must match first to avoid
  // triggering a different code path on length mismatch).
  if (cookie.length !== header.length) throw new CsrfError("mismatch");
  let diff = 0;
  for (let i = 0; i < cookie.length; i++) {
    diff |= cookie.charCodeAt(i) ^ header.charCodeAt(i);
  }
  if (diff !== 0) throw new CsrfError("mismatch");
}
