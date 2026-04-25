import "server-only";
import { NextRequest, NextResponse } from "next/server";

import { auth } from "@/auth";
import { engineFetch } from "@/lib/engine.server";
import { sanitizeErrorMessage } from "@/lib/redact.server";

export const runtime = "nodejs";

type BridgeStatus = {
  installed: boolean;
  enabled: boolean;
  policy: "owner_only" | "allowlist" | "open";
  owner_id: string | null;
  claim_code_present: boolean;
};

const DEFAULT_STATUS: BridgeStatus = {
  installed: false,
  enabled: false,
  policy: "owner_only",
  owner_id: null,
  claim_code_present: false,
};

export async function GET(_req: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  try {
    const upstream = await engineFetch("/engine/bridge");
    if (upstream.status === 404) {
      return NextResponse.json(DEFAULT_STATUS, { status: 200 });
    }
    const raw = await upstream.json().catch(() => null);
    if (!raw || typeof raw !== "object") {
      return NextResponse.json(DEFAULT_STATUS, { status: 200 });
    }
    return NextResponse.json(raw, { status: upstream.status });
  } catch (e) {
    return NextResponse.json(
      { error: sanitizeErrorMessage(String(e)) },
      { status: 502 },
    );
  }
}
