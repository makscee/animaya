/**
 * Edge-safe constant-time compare. Node's `crypto.timingSafeEqual` is
 * unavailable here; we substitute a length-guarded XOR loop.
 * Tracked as T-13-16 (review-accepted Edge substitute).
 */
export function edgeConstantTimeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}
