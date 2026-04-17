import "server-only";
import { NextRequest } from "next/server";

import { runMutation } from "@/lib/route-helpers.server";
import { BridgeClaimSchema } from "@/lib/schemas";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  return runMutation(req, BridgeClaimSchema, "/engine/bridge/regen", "POST");
}
