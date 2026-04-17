import "server-only";
import { NextRequest } from "next/server";

import { runMutation } from "@/lib/route-helpers.server";
import { BridgeTogglePayload } from "@/lib/schemas";

export const runtime = "nodejs";

export async function PUT(req: NextRequest) {
  return runMutation(req, BridgeTogglePayload, "/engine/bridge/toggle", "PUT");
}
