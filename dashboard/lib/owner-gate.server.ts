import "server-only";

/**
 * Owner-id equality gate (D-07). No first-login-wins fallback:
 *   - if either side is missing/empty → reject
 *   - otherwise string-compare (stringified to normalize number/string drift)
 *
 * Pure function; safe to unit-test without filesystem/next-auth.
 */
export function isOwner(
  provided: string | null | undefined,
  ownerId: string | null | undefined,
): boolean {
  if (!provided || !ownerId) return false;
  return String(provided) === String(ownerId);
}
