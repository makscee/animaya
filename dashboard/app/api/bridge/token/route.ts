import "server-only";
import { NextRequest } from "next/server";

import { runMutation } from "@/lib/route-helpers.server";
import { BridgeTokenPayload } from "@/lib/schemas";

export const runtime = "nodejs";

export async function PUT(req: NextRequest) {
  return runMutation(req, BridgeTokenPayload, "/engine/bridge/token", "PUT");
}
