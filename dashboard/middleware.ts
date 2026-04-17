import { getToken } from "next-auth/jwt";
import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = new Set<string>(["/login", "/403", "/api/health"]);
const isApiAuthPath = (p: string) => p.startsWith("/api/auth/");
const isStaticAsset = (p: string) =>
  p.startsWith("/_next/") || p === "/favicon.ico";

/**
 * Edge-safe owner gate. Reads `OWNER_TELEGRAM_ID` from env (populated at
 * install time from OWNER.md, Phase 11 contract). No fs access — Edge runtime
 * rule. Fail-closed if env unset.
 */
function isOwnerTelegramIdEdge(sub: string | null | undefined): boolean {
  if (!sub) return false;
  const owner = process.env.OWNER_TELEGRAM_ID;
  if (!owner) return false;
  return String(sub) === String(owner);
}

function buildCsp(_nonce: string): string {
  // Telegram Login Widget serves its script from https://telegram.org and
  // renders the author/bot avatar from https://t.me. `data:` URIs for
  // small inline images only.
  return [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' https://telegram.org",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https://t.me https://telegram.org",
    "font-src 'self' data:",
    "connect-src 'self'",
    "frame-src https://oauth.telegram.org",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");
}

function applySecurityHeaders(res: NextResponse, nonce: string): NextResponse {
  res.headers.set("Content-Security-Policy", buildCsp(nonce));
  res.headers.set(
    "Strict-Transport-Security",
    "max-age=63072000; includeSubDomains; preload",
  );
  res.headers.set("X-Frame-Options", "DENY");
  res.headers.set("X-Content-Type-Options", "nosniff");
  res.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  res.headers.set(
    "Permissions-Policy",
    "camera=(), microphone=(), geolocation=()",
  );
  return res;
}

/**
 * Edge-safe constant-time compare. Node's `crypto.timingSafeEqual` is
 * unavailable here; we substitute a length-guarded XOR loop.
 *
 * T-13-16 (threat model): accepting the Edge XOR approach is tracked as an
 * explicit risk. DASHBOARD_TOKEN is a shared secret behind Caddy TLS; the
 * XOR loop is length-guarded to avoid early-exit leakage beyond the universal
 * wrong-length signal.
 */
function edgeConstantTimeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export default async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const nonce = Buffer.from(
    crypto.getRandomValues(new Uint8Array(16)),
  ).toString("base64");

  const requestHeaders = new Headers(req.headers);
  requestHeaders.set("x-nonce", nonce);

  // ── DASHBOARD_TOKEN bypass (D-06) ────────────────────────────────────
  // Header or query param; constant-time compared. Used by scripted ops
  // and token-based deploy pipelines that cannot complete the Telegram
  // widget flow. Edge-safe XOR compare (no node:crypto available).
  const dashToken =
    req.headers.get("x-dashboard-token") ??
    req.nextUrl.searchParams.get("token");
  const expectedDashToken = process.env.DASHBOARD_TOKEN;
  if (
    dashToken &&
    expectedDashToken &&
    edgeConstantTimeEqual(dashToken, expectedDashToken)
  ) {
    const passRes = NextResponse.next({ request: { headers: requestHeaders } });
    return applySecurityHeaders(passRes, nonce);
  }

  // ── Public paths ─────────────────────────────────────────────────────
  if (
    PUBLIC_PATHS.has(pathname) ||
    isApiAuthPath(pathname) ||
    isStaticAsset(pathname)
  ) {
    const passRes = NextResponse.next({ request: { headers: requestHeaders } });
    return applySecurityHeaders(passRes, nonce);
  }

  // ── Session gate ─────────────────────────────────────────────────────
  // Decode raw JWT to read `sub`/`telegramId` directly — bypasses needing a
  // session() callback in middleware (Auth.js v5 would otherwise not expose
  // custom token fields through `req.auth.user`).
  const isProd = process.env.NODE_ENV === "production";
  const token = await getToken({
    req,
    secret: process.env.AUTH_SECRET,
    secureCookie: isProd,
    cookieName: isProd
      ? "__Secure-authjs.session-token"
      : "authjs.session-token",
  });
  if (!token) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    return applySecurityHeaders(NextResponse.redirect(url), nonce);
  }

  // ── Owner gate (D-07, Edge variant via OWNER_TELEGRAM_ID env) ────────
  const telegramId =
    typeof (token as { telegramId?: unknown }).telegramId === "string"
      ? (token as { telegramId: string }).telegramId
      : typeof token.sub === "string"
        ? token.sub
        : undefined;
  if (!isOwnerTelegramIdEdge(telegramId)) {
    const url = req.nextUrl.clone();
    url.pathname = "/403";
    return applySecurityHeaders(NextResponse.redirect(url), nonce);
  }

  if (telegramId) requestHeaders.set("x-user-telegram-id", telegramId);

  const res = NextResponse.next({ request: { headers: requestHeaders } });

  // ── CSRF double-submit cookie ───────────────────────────────────────
  if (!req.cookies.get("an-csrf")) {
    const bytes = new Uint8Array(32);
    crypto.getRandomValues(bytes);
    const csrfToken = Array.from(bytes, (b) =>
      b.toString(16).padStart(2, "0"),
    ).join("");
    res.cookies.set({
      name: "an-csrf",
      value: csrfToken,
      path: "/",
      sameSite: "strict",
      secure: isProd,
      httpOnly: false,
      maxAge: 28800,
    });
  }

  return applySecurityHeaders(res, nonce);
}

export const config = {
  // Match everything except Next.js internals and static files.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
