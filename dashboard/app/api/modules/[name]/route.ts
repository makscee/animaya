import "server-only";
import { NextRequest, NextResponse } from "next/server";

import { auth } from "@/auth";
import { engineFetch } from "@/lib/engine.server";
import { ModuleNameSchema } from "@/lib/schemas";
import { deepRedact, sanitizeErrorMessage } from "@/lib/redact.server";

export const runtime = "nodejs";

/**
 * GET /api/modules/[name]
 *
 * Returns `{name, version, description, installed, has_config, config}` for a
 * single module. Consumed by the /modules/[name] detail page to render the
 * config form (when installed) or an install CTA (when not).
 */
export async function GET(
  _req: NextRequest,
  ctx: { params: Promise<{ name: string }> },
) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  const { name } = await ctx.params;
  const nameParsed = ModuleNameSchema.safeParse(name);
  if (!nameParsed.success) {
    return NextResponse.json({ error: "invalid module name" }, { status: 400 });
  }
  try {
    const upstream = await engineFetch(
      `/engine/modules/${encodeURIComponent(nameParsed.data)}`,
    );
    if (upstream.status === 404) {
      return NextResponse.json({ error: "not found" }, { status: 404 });
    }
    const raw = (await upstream.json().catch(() => null)) as
      | Record<string, unknown>
      | null;
    if (!raw || typeof raw !== "object") {
      return NextResponse.json({ error: "bad upstream" }, { status: 502 });
    }
    const config =
      raw.config && typeof raw.config === "object" ? raw.config : {};
    return NextResponse.json(
      {
        name: raw.name,
        version: raw.version,
        description: raw.description,
        readme: typeof raw.readme === "string" ? raw.readme : "",
        config_schema:
          raw.config_schema && typeof raw.config_schema === "object"
            ? raw.config_schema
            : null,
        installed: Boolean(raw.installed),
        has_config: Boolean(raw.has_config),
        config: deepRedact(config),
      },
      { status: upstream.status },
    );
  } catch (e) {
    return NextResponse.json(
      { error: sanitizeErrorMessage(String(e)) },
      { status: 502 },
    );
  }
}
