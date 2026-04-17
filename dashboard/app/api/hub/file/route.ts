import "server-only";
import { NextRequest, NextResponse } from "next/server";
import { promises as fs } from "node:fs";

import { auth } from "@/auth";
import { safeResolve } from "@/lib/hub-tree.server";
import { HubFileQuery } from "@/lib/schemas";
import { sanitizeErrorMessage } from "@/lib/redact.server";

export const runtime = "nodejs";

const MAX_BYTES = 1_048_576; // 1 MiB — T-13-27.

/**
 * GET /api/hub/file?path=<rel>
 *
 * Read-only UTF-8 file content. Enforces:
 *   - safeResolve (traversal / symlink / DENY)
 *   - 1 MB size cap (415 if exceeded)
 *   - UTF-8-only (binary rejected with 415)
 */
export async function GET(req: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  const { searchParams } = new URL(req.url);
  const parsed = HubFileQuery.safeParse({ path: searchParams.get("path") });
  if (!parsed.success) {
    return NextResponse.json(
      { error: "invalid input", issues: parsed.error.issues },
      { status: 400 },
    );
  }
  let abs: string;
  try {
    abs = await safeResolve(parsed.data.path);
  } catch (e) {
    return NextResponse.json(
      { error: sanitizeErrorMessage(String(e instanceof Error ? e.message : e)) },
      { status: 403 },
    );
  }
  try {
    const stat = await fs.stat(abs);
    if (!stat.isFile()) {
      return NextResponse.json({ error: "not a file" }, { status: 400 });
    }
    if (stat.size > MAX_BYTES) {
      return NextResponse.json(
        { error: "file too large", max: MAX_BYTES, size: stat.size },
        { status: 415 },
      );
    }
    const buf = await fs.readFile(abs);
    // Reject binary — any NUL byte in the first KiB is a strong signal.
    const probe = buf.subarray(0, Math.min(1024, buf.length));
    for (let i = 0; i < probe.length; i++) {
      if (probe[i] === 0) {
        return NextResponse.json(
          { error: "binary file unsupported" },
          { status: 415 },
        );
      }
    }
    return NextResponse.json({
      path: parsed.data.path,
      size: stat.size,
      content: buf.toString("utf8"),
    });
  } catch (e) {
    return NextResponse.json(
      { error: sanitizeErrorMessage(String(e instanceof Error ? e.message : e)) },
      { status: 403 },
    );
  }
}
