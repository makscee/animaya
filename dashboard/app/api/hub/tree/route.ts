import "server-only";
import { NextRequest, NextResponse } from "next/server";

import { auth } from "@/auth";
import { listDir } from "@/lib/hub-tree.server";
import { HubTreeQuery } from "@/lib/schemas";
import { sanitizeErrorMessage } from "@/lib/redact.server";

export const runtime = "nodejs";

/**
 * GET /api/hub/tree?path=<rel>&show_hidden=<bool>
 *
 * Read-only file listing under HUB_ROOT. `listDir` enforces path-traversal,
 * symlink-escape, and DENY/DENY_PREFIX checks. Any Error surfaces as 403 —
 * we deliberately collapse the reasons so an attacker can't distinguish
 * "traversal blocked" from "DENY hit" from "doesn't exist".
 */
export async function GET(req: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  const { searchParams } = new URL(req.url);
  const parsed = HubTreeQuery.safeParse({
    path: searchParams.get("path") ?? "",
    show_hidden: searchParams.get("show_hidden") ?? false,
  });
  if (!parsed.success) {
    return NextResponse.json(
      { error: "invalid input", issues: parsed.error.issues },
      { status: 400 },
    );
  }
  try {
    const entries = await listDir(parsed.data.path, {
      showHidden: parsed.data.show_hidden,
    });
    return NextResponse.json({ path: parsed.data.path, entries });
  } catch (e) {
    // Path-safety, DENY, or ENOENT — all collapse to 403.
    return NextResponse.json(
      { error: sanitizeErrorMessage(String(e instanceof Error ? e.message : e)) },
      { status: 403 },
    );
  }
}
