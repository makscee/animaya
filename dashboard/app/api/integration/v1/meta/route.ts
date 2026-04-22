import "server-only";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

/**
 * GET /api/integration/v1/meta
 *
 * Version + capabilities probe for voidnet-api. Auth is enforced entirely by
 * `dashboard/middleware.ts` (voidnet HMAC branch or Telegram session). This
 * handler only runs after the request has cleared the gate, so it simply
 * returns the locked response shape.
 *
 * Response shape (REQ-SPEC-07):
 *   { version, supported_auth_modes: ["telegram", "voidnet"], dashboard_port }
 */
export async function GET() {
  const pkg = JSON.parse(
    readFileSync(join(process.cwd(), "package.json"), "utf-8"),
  ) as { version: string };
  return NextResponse.json({
    version: pkg.version,
    supported_auth_modes: ["telegram", "voidnet"],
    dashboard_port: Number(process.env.DASHBOARD_PORT ?? 8090),
  });
}
