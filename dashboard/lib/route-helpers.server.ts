import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import type { ZodType } from "zod";

import { auth } from "@/auth";
import { CsrfError, verifyCsrf } from "@/lib/csrf.server";
import { engineFetch } from "@/lib/engine.server";
import { sanitizeErrorMessage } from "@/lib/redact.server";

/**
 * Standard mutation-route template (PATTERNS.md §Standard template).
 *
 * Enforces: session → CSRF → zod → engineFetch with `web:<id>` session_key
 * (SEC-02). Returns 401/403/400/502 on the respective failure classes.
 */
export async function runMutation<T>(
  req: NextRequest,
  schema: ZodType<T>,
  enginePath: string,
  method: "POST" | "PUT" | "DELETE" = "POST",
): Promise<NextResponse> {
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
  const body = await req.json().catch(() => null);
  // Treat a body of null (failed parse or empty body on no-input routes) as
  // an empty object so schemas like `z.object({})` succeed.
  const candidate = body ?? {};
  const parsed = schema.safeParse(candidate);
  if (!parsed.success) {
    return NextResponse.json(
      { error: "invalid input", issues: parsed.error.issues },
      { status: 400 },
    );
  }
  try {
    const upstream = await engineFetch(enginePath, {
      method,
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        ...(parsed.data as object),
        session_key: `web:${session.user.id}`,
      }),
    });
    const data = await upstream.json().catch(() => ({}));
    return NextResponse.json(data, { status: upstream.status });
  } catch (e) {
    return NextResponse.json(
      { error: sanitizeErrorMessage(String(e)) },
      { status: 502 },
    );
  }
}
