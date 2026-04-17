import "server-only";
import { NextRequest } from "next/server";

import { runMutation } from "@/lib/route-helpers.server";
import { BridgePolicyPayload } from "@/lib/schemas";

export const runtime = "nodejs";

export async function PUT(req: NextRequest) {
  return runMutation(req, BridgePolicyPayload, "/engine/bridge/policy", "PUT");
}
