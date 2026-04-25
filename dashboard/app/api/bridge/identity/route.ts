import "server-only";
import { NextRequest, NextResponse } from "next/server";

import { auth } from "@/auth";
import { engineFetch } from "@/lib/engine.server";
import { sanitizeErrorMessage } from "@/lib/redact.server";

export const runtime = "nodejs";

type Identity = {
  ok: boolean;
  username: string | null;
  error: string | null;
};

const DEFAULT: Identity = { ok: false, username: null, error: null };

export async function GET(_req: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  try {
    const upstream = await engineFetch("/engine/bridge/identity");
    const raw = await upstream.json().catch(() => null);
    if (!raw || typeof raw !== "object") {
      return NextResponse.json(DEFAULT, { status: 200 });
    }
    return NextResponse.json(raw, { status: upstream.status });
  } catch (e) {
    return NextResponse.json(
      { error: sanitizeErrorMessage(String(e)) },
      { status: 502 },
    );
  }
}
