import "server-only";
import { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";

import { auth } from "@/auth";
import { CsrfError, verifyCsrf } from "@/lib/csrf.server";
import { engineFetch } from "@/lib/engine.server";
import { ModuleNameSchema } from "@/lib/schemas";
import { sanitizeErrorMessage } from "@/lib/redact.server";

export const runtime = "nodejs";

const UninstallBody = z.object({}).catchall(z.unknown());

export async function POST(
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
  const body = (await req.json().catch(() => null)) ?? {};
  const parsed = UninstallBody.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      { error: "invalid input", issues: parsed.error.issues },
      { status: 400 },
    );
  }
  try {
    const upstream = await engineFetch(
      `/engine/modules/${encodeURIComponent(nameParsed.data)}/uninstall`,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          ...parsed.data,
          session_key: `web:${session.user.id}`,
        }),
      },
    );
    const data = await upstream.json().catch(() => ({}));
    return NextResponse.json(data, { status: upstream.status });
  } catch (e) {
    return NextResponse.json(
      { error: sanitizeErrorMessage(String(e)) },
      { status: 502 },
    );
  }
}
