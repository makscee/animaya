import { encode, getToken } from "next-auth/jwt";
import { NextRequest, NextResponse } from "next/server";
import { edgeConstantTimeEqual } from "@/lib/ct-compare";
import {
  verifyVoidnetHeaders,
  type VoidnetClaims,
} from "@/lib/voidnet-auth.server";

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

const VOIDNET_SESSION_MAX_AGE = 60 * 60 * 8; // 8h, mirrors Telegram session

async function mintVoidnetSession(
  claims: VoidnetClaims,
  isProd: boolean,
): Promise<string> {
  return encode({
    token: {
      sub: claims.telegramId,
      telegramId: claims.telegramId,
      name: claims.handle,
      src: "voidnet", // debug-only marker; downstream MUST NOT branch on this
    },
    secret: process.env.AUTH_SECRET!,
    maxAge: VOIDNET_SESSION_MAX_AGE,
    salt: isProd ? "__Secure-authjs.session-token" : "authjs.session-token",
  });
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
    // CR-01 (Phase 13 review): the bypass must not silently reuse an existing
    // next-auth session cookie, or downstream routes would mint
    // `web:<ownerId>` session_keys from a request that was never re-gated for
    // owner equality. Strip the session cookie for this request and flag the
    // origin as ops-token so routes can distinguish and (optionally) accept.
    requestHeaders.set("x-animaya-ops", "1");
    const rawCookie = req.headers.get("cookie") ?? "";
    const cleanedCookie = rawCookie
      .split(/;\s*/)
      .filter(
        (c) =>
          !/^(?:__Secure-)?authjs\.session-token=/.test(c) &&
          !/^(?:__Secure-)?next-auth\.session-token=/.test(c),
      )
      .join("; ");
    requestHeaders.set("cookie", cleanedCookie);
    const passRes = NextResponse.next({ request: { headers: requestHeaders } });
    return applySecurityHeaders(passRes, nonce);
  }

  // ── VoidNet HMAC header auth (REQ-SPEC-03/04/06) ─────────────────────
  // Activation: VOIDNET_HMAC_SECRET env + X-Voidnet-Signature header both
  // present. Unset secret → skip entirely (backward compat with standalone
  // Telegram deployments).
  const voidnetSecret = process.env.VOIDNET_HMAC_SECRET;
  const hasVoidnetSig = req.headers.get("x-voidnet-signature");
  if (voidnetSecret && hasVoidnetSig) {
    const isProdVoidnet = process.env.NODE_ENV === "production";
    const result = await verifyVoidnetHeaders(
      req.headers,
      voidnetSecret,
      process.env.OWNER_TELEGRAM_ID,
    );
    if (!result.ok) {
      return applySecurityHeaders(
        NextResponse.json(
          { error: result.error, code: result.code },
          { status: result.status },
        ),
        nonce,
      );
    }
    const jwt = await mintVoidnetSession(result.claims, isProdVoidnet);
    requestHeaders.set("x-user-telegram-id", result.claims.telegramId);
    const passRes = NextResponse.next({ request: { headers: requestHeaders } });
    passRes.cookies.set({
      name: isProdVoidnet
        ? "__Secure-authjs.session-token"
        : "authjs.session-token",
      value: jwt,
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      secure: isProdVoidnet,
      maxAge: VOIDNET_SESSION_MAX_AGE,
    });
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
    if (pathname.startsWith("/api/integration/v1/")) {
      return applySecurityHeaders(
        NextResponse.json(
          { error: "unauthorized", code: "NO_SESSION" },
          { status: 401 },
        ),
        nonce,
      );
    }
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
    if (pathname.startsWith("/api/integration/v1/")) {
      return applySecurityHeaders(
        NextResponse.json(
          { error: "forbidden", code: "NOT_OWNER" },
          { status: 403 },
        ),
        nonce,
      );
    }
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
