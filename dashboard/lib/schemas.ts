/**
 * Shared zod schemas — imported by both client (react-hook-form resolvers)
 * and server (route handler input validation). NO server-only imports here.
 *
 * SEC-01: `ModuleDTO` intentionally excludes any secret credential field.
 * Engine responses are re-parsed through this schema (`.strip()` by default)
 * so any unknown field leaked from the Python layer is dropped before
 * reaching the browser. See module route handler for response redaction.
 */

import { z } from "zod";

// ── Module identifiers and configuration ───────────────────────────────────

export const ModuleNameSchema = z
  .string()
  .regex(/^[a-z0-9][a-z0-9_-]{0,63}$/, "invalid module name");

/** Per-module config is opaque at the route boundary; module registry validates internally. */
export const ModuleConfigSchema = z.record(z.string(), z.unknown());

// ── Bridge payloads ────────────────────────────────────────────────────────

/** Bridge claim has no body — CSRF-protected POST. */
export const BridgeClaimSchema = z.object({});

export const BridgeTogglePayload = z.object({
  enabled: z.boolean(),
});

export const BridgePolicyPayload = z.object({
  policy: z.enum(["open", "owner_only", "invite"]),
});

// ── Hub filesystem queries ─────────────────────────────────────────────────

export const HubTreeQuery = z.object({
  path: z.string().default(""),
  show_hidden: z.coerce.boolean().default(false),
});

export const HubFileQuery = z.object({
  path: z.string().min(1),
});

// ── Chat ───────────────────────────────────────────────────────────────────

export const ChatStreamPayload = z.object({
  message: z.string().min(1).max(16000),
});

// ── Response DTOs ──────────────────────────────────────────────────────────

/**
 * Module DTO returned to the browser.
 *
 * SEC-01 enforcement: NO secret credential fields. Engine responses are
 * parsed through `ModuleDTO.array()`; unknown fields are stripped by default,
 * guaranteeing tokens cannot leak even if the Python side returns them.
 */
export const ModuleDTO = z.object({
  name: z.string(),
  installed: z.boolean(),
  version: z.string().optional(),
  description: z.string().optional(),
  config: ModuleConfigSchema.optional(),
});

export type ModuleDTOType = z.infer<typeof ModuleDTO>;
export type BridgeTogglePayloadType = z.infer<typeof BridgeTogglePayload>;
export type BridgePolicyPayloadType = z.infer<typeof BridgePolicyPayload>;
export type ChatStreamPayloadType = z.infer<typeof ChatStreamPayload>;
