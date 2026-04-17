import "server-only";
import { NextRequest, NextResponse } from "next/server";

import { auth } from "@/auth";
import { CsrfError, verifyCsrf } from "@/lib/csrf.server";
import { engineFetch } from "@/lib/engine.server";
import { sanitizeErrorMessage } from "@/lib/redact.server";
import { ChatStreamPayload } from "@/lib/schemas";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * POST /api/chat/stream
 *
 * SSE proxy from the Python engine (/engine/chat) to the browser. Runtime
 * pinned to `nodejs` because (a) Web Streams + long-lived connections are
 * fragile on Edge, and (b) the CSRF/redact helpers import `server-only`
 * and `node:crypto`.
 *
 * Caddy pitfall: `X-Accel-Buffering: no` + `Cache-Control: no-store, no-transform`
 * prevents intermediate buffering. The heartbeat (`:ping` comment line every
 * 15s) keeps the connection warm through idle proxies and gives clients a
 * timeout anchor. See 13-RESEARCH.md Pitfall 3.
 *
 * Manual verify recipe (for Plan 05 Playwright):
 *   curl -N -X POST http://127.0.0.1:8090/api/chat/stream \
 *     -H 'content-type: application/json' \
 *     -H 'x-dashboard-token: test-dash-token' \
 *     -H 'x-csrf-token: <cookie>' \
 *     --cookie 'an-csrf=<cookie>' \
 *     -d '{"message":"ping"}'
 */
export async function POST(req: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return new NextResponse("", { status: 401 });
  }
  try {
    verifyCsrf(req);
  } catch (e) {
    if (e instanceof CsrfError) {
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }
    throw e;
  }
  const parsed = ChatStreamPayload.safeParse(
    await req.json().catch(() => null),
  );
  if (!parsed.success) {
    return NextResponse.json({ error: "invalid input" }, { status: 400 });
  }

  let upstream: Response;
  try {
    upstream = await engineFetch("/engine/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        ...parsed.data,
        session_key: `web:${session.user.id}`,
      }),
    });
  } catch (e) {
    return NextResponse.json(
      { error: sanitizeErrorMessage(String(e)) },
      { status: 502 },
    );
  }

  if (!upstream.body) {
    return new NextResponse("", { status: 502 });
  }

  // Heartbeat: inject `:ping\n\n` SSE comment every 15s onto the passthrough.
  const encoder = new TextEncoder();
  const { readable, writable } = new TransformStream<Uint8Array, Uint8Array>();
  const writer = writable.getWriter();
  const ping = setInterval(() => {
    writer.write(encoder.encode(":ping\n\n")).catch(() => {});
  }, 15000);

  (async () => {
    const reader = upstream.body!.getReader();
    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        if (value) await writer.write(value);
      }
    } finally {
      clearInterval(ping);
      await writer.close().catch(() => {});
    }
  })();

  return new NextResponse(readable, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-store, no-transform",
      "X-Accel-Buffering": "no",
      Connection: "keep-alive",
    },
  });
}
