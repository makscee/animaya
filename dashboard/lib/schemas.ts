import { z } from "zod";

/**
 * Shared zod schemas used by dashboard forms + API route handlers.
 *
 * This file is the source of truth for Plan 13-05 UI (rhf + zodResolver) and
 * Plan 13-03 route handlers (server-side parse). Keep field-level messages
 * stable — they surface directly to the operator via FormMessage.
 */

// ── Chat ───────────────────────────────────────────────────────────────────
export const ChatSendPayload = z.object({
  message: z.string().min(1, "Message cannot be empty").max(8000),
  session_id: z.string().optional(),
});
export type ChatSendPayload = z.infer<typeof ChatSendPayload>;

// ── Modules ────────────────────────────────────────────────────────────────
// Module config is heterogeneous across modules; accept any JSON-shaped dict
// and let the engine validate module-specific fields. The form renders the
// JSON editor fallback when a module declares no fields.
export const ModuleConfigSchema = z.object({
  config: z.record(z.string(), z.unknown()),
});
export type ModuleConfigPayload = z.infer<typeof ModuleConfigSchema>;

// ── Bridge ─────────────────────────────────────────────────────────────────
export const BridgeTogglePayload = z.object({
  enabled: z.boolean(),
});
export type BridgeTogglePayload = z.infer<typeof BridgeTogglePayload>;

export const BridgePolicyPayload = z.object({
  policy: z.enum(["owner_only", "allowlist", "open"]),
});
export type BridgePolicyPayload = z.infer<typeof BridgePolicyPayload>;

export const BridgeClaimPayload = z.object({
  code: z.string().min(4, "Claim code required"),
});
export type BridgeClaimPayload = z.infer<typeof BridgeClaimPayload>;
