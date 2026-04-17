import "server-only";

/**
 * Loopback client to the Python engine (FastAPI). Port 8091 is the default
 * internal port — the Next.js dashboard owns the public port 8090 (D-02).
 * Override via `ANIMAYA_ENGINE_URL` for tests or alternative deployments.
 */
function resolveEngineUrl(): string {
  return process.env.ANIMAYA_ENGINE_URL ?? "http://127.0.0.1:8091";
}

export function getEngineUrl(): string {
  return resolveEngineUrl();
}

/**
 * Loopback fetch to the Python engine. Always `cache: "no-store"` so Next.js
 * never caches engine responses (SSE streams, stateful module ops).
 *
 * Caller is responsible for `session_key: "web:<id>"` namespacing (SEC-02).
 */
export async function engineFetch(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  return fetch(`${resolveEngineUrl()}${path}`, { cache: "no-store", ...init });
}
