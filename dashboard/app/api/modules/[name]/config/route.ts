import "server-only";
import { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { auth } from "@/auth";
import { CsrfError, verifyCsrf } from "@/lib/csrf.server";
import { engineFetch } from "@/lib/engine.server";
import { ModuleConfigSchema, ModuleNameSchema } from "@/lib/schemas";
import { sanitizeErrorMessage } from "@/lib/redact.server";

export const runtime = "nodejs";

/** Redact well-known credential fields from a module config response. */
function redactConfig(cfg: unknown): unknown {
  if (!cfg || typeof cfg !== "object") return cfg;
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(cfg as Record<string, unknown>)) {
    if (/token|secret|api_key|apikey|password/i.test(k)) {
      out[k] = "[REDACTED]";
    } else {
      out[k] = v;
    }
  }
  return out;
}

export async function PUT(
  req: NextRequest,
  ctx: { params: Promise<{ name: string }> },
) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  try {
    verifyCsrf(req);
  } catch (e) {
    if (e instanceof CsrfError) {
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }
    throw e;
  }
  const { name } = await ctx.params;
  const nameParsed = ModuleNameSchema.safeParse(name);
  if (!nameParsed.success) {
    return NextResponse.json({ error: "invalid module name" }, { status: 400 });
  }
  const body = await req.json().catch(() => null);
  const parsed = ModuleConfigSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      { error: "invalid input", issues: parsed.error.issues },
      { status: 400 },
    );
  }
  try {
    const upstream = await engineFetch(
      `/engine/modules/${encodeURIComponent(nameParsed.data)}/config`,
      {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          ...parsed.data,
          session_key: `web:${session.user.id}`,
        }),
      },
    );
    const data = (await upstream.json().catch(() => ({}))) as Record<
      string,
      unknown
    >;
    if (data && typeof data === "object" && "config" in data) {
      data.config = redactConfig(data.config);
    }
    return NextResponse.json(data, { status: upstream.status });
  } catch (e) {
    return NextResponse.json(
      { error: sanitizeErrorMessage(String(e)) },
      { status: 502 },
    );
  }
}
