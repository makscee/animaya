import "server-only";
import fs from "node:fs/promises";
import path from "node:path";

/**
 * OWNER.md contract (Phase 11 output, consumed by D-07):
 *   The file must contain a line matching `^telegram_id:\s*<number>$` (case-insensitive).
 *   Other content is ignored. Missing file or missing line → `readOwnerId()` returns null,
 *   which causes signIn() to reject (fail-closed; no first-login-wins fallback).
 *
 * Location resolution order:
 *   1. `OWNER_MD_PATH` env var (test/dev override)
 *   2. `$HOME/hub/knowledge/animaya/OWNER.md` (Phase 11 install default)
 */
function resolveOwnerPath(): string {
  const override = process.env.OWNER_MD_PATH;
  if (override) return override;
  const home = process.env.HOME ?? "";
  return path.resolve(home, "hub/knowledge/animaya/OWNER.md");
}

let cached: string | null | undefined = undefined;

export async function readOwnerId(): Promise<string | null> {
  if (cached !== undefined) return cached;
  try {
    const raw = await fs.readFile(resolveOwnerPath(), "utf8");
    const match = raw.match(/^telegram_id:\s*(\d+)\s*$/im);
    cached = match ? match[1] : null;
  } catch {
    cached = null;
  }
  return cached;
}

/** Test-only: reset the cache. */
export function _resetOwnerCache(): void {
  cached = undefined;
}
