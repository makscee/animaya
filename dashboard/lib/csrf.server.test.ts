import { describe, test, expect } from "bun:test";
import * as fs from "node:fs";
import * as path from "node:path";
import { NextRequest } from "next/server";

import {
  verifyCsrf,
  generateCsrfToken,
  csrfCookie,
  CsrfError,
  CSRF_COOKIE_NAME,
  CSRF_HEADER_NAME,
  EXPECTED_ORIGIN,
} from "./csrf.server";

function buildReq(opts: {
  origin?: string | null;
  cookie?: string | null;
  header?: string | null;
}): NextRequest {
  const headers = new Headers();
  if (opts.origin != null) headers.set("origin", opts.origin);
  if (opts.header != null) headers.set(CSRF_HEADER_NAME, opts.header);
  if (opts.cookie != null) headers.set("cookie", `${CSRF_COOKIE_NAME}=${opts.cookie}`);
  return new NextRequest(new Request(`${EXPECTED_ORIGIN}/api/test`, {
    method: "POST",
    headers,
  }));
}

describe("issueCsrfCookie / csrfCookie", () => {
  test("returns a Set-Cookie header with Path=/, SameSite=Strict, Secure, Max-Age", () => {
    const token = generateCsrfToken();
    expect(token.length).toBeGreaterThanOrEqual(32);
    const cookie = csrfCookie(token);
    expect(cookie).toContain(`${CSRF_COOKIE_NAME}=${token}`);
    expect(cookie).toContain("Path=/");
    expect(cookie).toContain("SameSite=Strict");
    expect(cookie).toContain("Secure");
    expect(cookie).not.toContain("HttpOnly");
    expect(cookie).toMatch(/Max-Age=\d+/);
  });
});

describe("verifyCsrf", () => {
  const goodToken = "a".repeat(64);

  test("accepts when cookie === header and length >= 32", () => {
    const req = buildReq({ origin: EXPECTED_ORIGIN, cookie: goodToken, header: goodToken });
    expect(() => verifyCsrf(req)).not.toThrow();
  });

  test("rejects when cookie missing", () => {
    const req = buildReq({ origin: EXPECTED_ORIGIN, cookie: null, header: goodToken });
    expect(() => verifyCsrf(req)).toThrow(CsrfError);
  });

  test("rejects when header missing", () => {
    const req = buildReq({ origin: EXPECTED_ORIGIN, cookie: goodToken, header: null });
    expect(() => verifyCsrf(req)).toThrow(CsrfError);
  });

  test("rejects when values differ", () => {
    const req = buildReq({ origin: EXPECTED_ORIGIN, cookie: goodToken, header: "b".repeat(64) });
    expect(() => verifyCsrf(req)).toThrow(CsrfError);
  });

  test("rejects when Origin header does not match expected origin (cross-origin)", () => {
    const req = buildReq({ origin: "https://attacker.example", cookie: goodToken, header: goodToken });
    expect(() => verifyCsrf(req)).toThrow(CsrfError);
  });

  test("rejects when Origin and Referer are both missing", () => {
    const req = buildReq({ origin: null, cookie: goodToken, header: goodToken });
    expect(() => verifyCsrf(req)).toThrow(CsrfError);
  });

  test("accepts Referer fallback when Origin missing and referer matches", () => {
    const headers = new Headers();
    headers.set("referer", `${EXPECTED_ORIGIN}/modules`);
    headers.set(CSRF_HEADER_NAME, goodToken);
    headers.set("cookie", `${CSRF_COOKIE_NAME}=${goodToken}`);
    const req = new NextRequest(
      new Request(`${EXPECTED_ORIGIN}/api/test`, { method: "POST", headers }),
    );
    expect(() => verifyCsrf(req)).not.toThrow();
  });
});

describe("csrf.shared.ts is neutral (no server-only)", () => {
  test("file contains no 'server-only' string and exports all three constants", () => {
    const p = path.join(process.cwd(), "lib", "csrf.shared.ts");
    const src = fs.readFileSync(p, "utf-8");
    expect(src).not.toContain("server-only");
    expect(src).toContain("CSRF_COOKIE_NAME");
    expect(src).toContain("CSRF_HEADER_NAME");
    expect(src).toContain("EXPECTED_ORIGIN");
  });
});
