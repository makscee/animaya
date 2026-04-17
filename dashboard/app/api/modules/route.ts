import "server-only";
import { NextRequest, NextResponse } from "next/server";

import { auth } from "@/auth";
import { engineFetch } from "@/lib/engine.server";
import { ModuleDTO } from "@/lib/schemas";
import { deepRedact, sanitizeErrorMessage } from "@/lib/redact.server";

export const runtime = "nodejs";

/**
 * GET /api/modules
 *
 * SEC-01: Engine response is re-parsed through `ModuleDTO.array()` before
 * returning to the browser. Unknown fields (e.g., any bot-secret field) are
 * stripped by zod's default strip mode, so tokens cannot leak even if the
 * Python engine accidentally includes them.
 *
 * Middleware already enforces session OR DASHBOARD_TOKEN before reaching
 * this handler. We still check `auth()` so any request that slipped past
 * (e.g., edge-case routing) is rejected.
 */
export async function GET(_req: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  try {
    const upstream = await engineFetch("/engine/modules");
    const raw = await upstream.json().catch(() => ({}));
    const list = Array.isArray(raw?.modules) ? raw.modules : [];
    const parsed = ModuleDTO.array().safeParse(list);
    // CR-02 (Phase 13 review): `ModuleConfigSchema = z.record(z.string(),
    // z.unknown())` accepts arbitrary keys, so zod alone does NOT strip
    // secret-named fields nested under `config`. Deep-redact as a second
    // barrier, mirroring the Python-side `_scrub_mapping` scrubber.
    const modules = parsed.success ? deepRedact(parsed.data) : [];
    return NextResponse.json({ modules }, { status: upstream.status });
  } catch (e) {
    return NextResponse.json(
      { error: sanitizeErrorMessage(String(e)) },
      { status: 502 },
    );
  }
}
