import "server-only";

import { promises as fs } from "node:fs";
import * as path from "node:path";
import * as os from "node:os";

/**
 * Hub file-tree reader with path-traversal + symlink-escape defense (DASH-04).
 *
 * Defense layers:
 *   1. `path.resolve(HUB_ROOT, rel)` collapses `..` segments
 *   2. `fs.realpath` follows symlinks and returns the on-disk canonical path
 *   3. Prefix-check: canonical path must start with `HUB_ROOT + sep` (or equal HUB_ROOT)
 *   4. DENY set blocks well-known sensitive entries (e.g., `.git/hooks`, `.ssh`)
 *   5. DENY_PREFIX blocks dotfile classes that often carry secrets (e.g., `.env`)
 *
 * Tests may override HUB_ROOT via `HUB_ROOT_OVERRIDE` env var.
 */

function resolveHubRoot(): string {
  const override = process.env.HUB_ROOT_OVERRIDE;
  if (override) return override;
  return path.join(os.homedir(), "hub");
}

export function getHubRoot(): string {
  return resolveHubRoot();
}

/** Exact relative paths that MUST NOT be readable regardless of session. */
const DENY: ReadonlySet<string> = new Set([
  ".git",
  ".git/hooks",
  ".git/config",
  ".ssh",
  ".aws",
  ".gnupg",
]);

/** Relative-path prefixes that MUST NOT be readable (dotfile secret classes). */
const DENY_PREFIX: readonly string[] = [".env", ".netrc", ".pypirc"];

function normalizeRel(rel: string): string {
  // Strip leading slash; collapse backslashes to forward slashes so checks
  // are platform-consistent.
  return rel.replace(/^[/\\]+/, "").replace(/\\/g, "/");
}

function isDenied(rel: string): boolean {
  const norm = normalizeRel(rel);
  if (!norm) return false;
  for (const entry of DENY) {
    if (norm === entry || norm.startsWith(entry + "/")) return true;
  }
  for (const prefix of DENY_PREFIX) {
    if (norm === prefix || norm.startsWith(prefix + "/") || norm.startsWith(prefix + ".")) {
      return true;
    }
    // Also deny segment-local hits (e.g., `sub/.env`).
    const segments = norm.split("/");
    for (const seg of segments) {
      if (seg === prefix || seg.startsWith(prefix + ".")) return true;
    }
  }
  return false;
}

/**
 * Safely resolve a relative path under HUB_ROOT.
 * Throws on traversal, symlink escape, or DENY hit.
 */
export async function safeResolve(rel: string): Promise<string> {
  const root = resolveHubRoot();
  const rootReal = await fs.realpath(root);
  const norm = normalizeRel(rel ?? "");

  if (isDenied(norm)) {
    throw new Error("forbidden path");
  }

  // Step 1: lexical resolve inside the advertised root.
  const joined = path.resolve(rootReal, norm);

  // Step 2: canonicalize. If the target does not exist yet, realpath on the
  // nearest existing ancestor and re-append the remainder.
  //
  // WR-03 (Phase 13 review): the old fallback silently assigned `canonical =
  // joined` when NO ancestor resolved, which would defeat the symlink-escape
  // prefix check on a broken root. We now rely on the `fs.realpath(root)`
  // call at the top of this function (which throws if the root is missing)
  // and require canonicalization to succeed — otherwise throw.
  let canonical: string | undefined;
  try {
    canonical = await fs.realpath(joined);
  } catch {
    let cursor = joined;
    const trailing: string[] = [];
    while (cursor !== path.dirname(cursor)) {
      try {
        const anc = await fs.realpath(cursor);
        canonical = path.join(anc, ...trailing.reverse());
        break;
      } catch {
        trailing.push(path.basename(cursor));
        cursor = path.dirname(cursor);
      }
    }
  }
  if (!canonical) {
    // rootReal exists (resolved at line 74), so every real path within it has
    // at least one canonicalizable ancestor. Reaching here means the caller
    // supplied a pathological input; fail closed instead of trusting the
    // lexical path.
    throw new Error("path cannot be canonicalized");
  }

  // Step 3: prefix-check against canonical root.
  if (canonical !== rootReal && !canonical.startsWith(rootReal + path.sep)) {
    throw new Error("path escapes hub root");
  }

  // Re-check DENY on the canonical-relative path (defence against symlinks
  // that dodge the lexical check).
  const canonicalRel = path.relative(rootReal, canonical);
  if (canonicalRel && isDenied(canonicalRel)) {
    throw new Error("forbidden path");
  }

  return canonical;
}

export interface HubEntry {
  name: string;
  path: string; // relative to HUB_ROOT, POSIX-style
  type: "file" | "dir";
  size?: number;
}

export interface ListDirOptions {
  showHidden?: boolean;
}

export async function listDir(
  rel: string,
  opts: ListDirOptions = {},
): Promise<HubEntry[]> {
  const root = await fs.realpath(resolveHubRoot());
  const abs = await safeResolve(rel);
  const stat = await fs.stat(abs);
  if (!stat.isDirectory()) {
    throw new Error("not a directory");
  }
  const entries = await fs.readdir(abs, { withFileTypes: true });
  const result: HubEntry[] = [];
  for (const e of entries) {
    if (!opts.showHidden && e.name.startsWith(".")) continue;
    const childAbs = path.join(abs, e.name);
    const childRel = path.relative(root, childAbs).split(path.sep).join("/");
    if (isDenied(childRel)) continue;
    const type: "file" | "dir" = e.isDirectory() ? "dir" : "file";
    let size: number | undefined;
    if (type === "file") {
      try {
        const st = await fs.stat(childAbs);
        size = st.size;
      } catch {
        size = undefined;
      }
    }
    result.push({ name: e.name, path: childRel, type, size });
  }
  // Dir-first, then name.
  result.sort((a, b) => {
    if (a.type !== b.type) return a.type === "dir" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
  return result;
}
