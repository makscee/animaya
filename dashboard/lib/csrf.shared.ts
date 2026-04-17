// csrf.shared.ts — constants shared between client and server.
// This module is NEUTRAL (isomorphic): it must remain free of any runtime
// sentinel that would poison the client bundle. Safe to import from .tsx
// client components.

export const CSRF_COOKIE_NAME = "an-csrf";
export const CSRF_HEADER_NAME = "x-csrf-token";

// Resolution order:
//   1. NEXT_PUBLIC_ANIMAYA_PUBLIC_ORIGIN — inlined into the client bundle at build.
//   2. ANIMAYA_PUBLIC_ORIGIN              — runtime override set by the process env.
//   3. Fallback to the production animaya URL.
// The client-visible NEXT_PUBLIC_ variant is deliberate: the api-client needs
// the same origin string to construct fetch URLs, and Next.js only inlines
// env vars prefixed with NEXT_PUBLIC_.
export const EXPECTED_ORIGIN =
  process.env.NEXT_PUBLIC_ANIMAYA_PUBLIC_ORIGIN ??
  process.env.ANIMAYA_PUBLIC_ORIGIN ??
  "https://animaya.makscee.ru";
