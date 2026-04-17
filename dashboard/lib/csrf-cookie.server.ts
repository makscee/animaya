import "server-only";

import { cookies } from "next/headers";

import { generateCsrfToken, CSRF_COOKIE_NAME } from "./csrf.server";

/**
 * Ensure the CSRF double-submit cookie is present on the browser.
 *
 * Called from the `(auth)` layout's async server body on every render.
 * Idempotent: if the cookie is already set, this is a no-op.
 *
 * HttpOnly is intentionally `false` — client-side api-client reads the
 * value via `document.cookie` and mirrors it into the `x-csrf-token` request
 * header. SameSite=Strict + Secure + Origin-check on the server side defend
 * against cross-site read.
 *
 * Max-Age = 28800 (8h) matches the typical session TTL.
 */
export async function issueCsrfCookieOnce(): Promise<void> {
  const jar = await cookies();
  if (jar.get(CSRF_COOKIE_NAME)) return;
  const token = generateCsrfToken();
  jar.set({
    name: CSRF_COOKIE_NAME,
    value: token,
    path: "/",
    sameSite: "strict",
    secure: process.env.NODE_ENV === "production",
    httpOnly: false,
    maxAge: 28800,
  });
}
