import "server-only";
import crypto from "node:crypto";

/**
 * Constant-time compare for the DASHBOARD_TOKEN bypass (D-06).
 * Returns false fast on length mismatch (no timing leak about expected length
 * beyond the universal "wrong-length" signal) and on any missing value.
 * Node-only: middleware (Edge) must inline an equivalent XOR loop since
 * `crypto.timingSafeEqual` is unavailable in the Edge runtime.
 */
export function dashboardTokenMatches(
  provided: string | null | undefined,
  expected: string | null | undefined,
): boolean {
  if (!provided || !expected) return false;
  const a = Buffer.from(provided);
  const b = Buffer.from(expected);
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}
