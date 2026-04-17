import { describe, test, expect, beforeEach, afterEach } from "bun:test";

import { engineFetch, getEngineUrl } from "./engine.server";

const realFetch = globalThis.fetch;
let lastCall: { url: string; init?: RequestInit } | null = null;

beforeEach(() => {
  lastCall = null;
  globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
    lastCall = { url: String(url), init };
    return new Response("ok", { status: 200 });
  }) as typeof fetch;
});

afterEach(() => {
  globalThis.fetch = realFetch;
  delete process.env.ANIMAYA_ENGINE_URL;
});

describe("engineFetch", () => {
  test("resolves to upstream response when ANIMAYA_ENGINE_URL set", async () => {
    process.env.ANIMAYA_ENGINE_URL = "http://127.0.0.1:9999";
    const res = await engineFetch("/engine/ping");
    expect(res.status).toBe(200);
    expect(lastCall?.url).toBe("http://127.0.0.1:9999/engine/ping");
  });

  test("falls back to http://127.0.0.1:8091 when env unset", async () => {
    delete process.env.ANIMAYA_ENGINE_URL;
    await engineFetch("/engine/modules");
    expect(lastCall?.url).toBe("http://127.0.0.1:8091/engine/modules");
    expect(getEngineUrl()).toBe("http://127.0.0.1:8091");
  });

  test('passes cache: "no-store"', async () => {
    await engineFetch("/engine/x");
    expect((lastCall?.init as RequestInit | undefined)?.cache).toBe("no-store");
  });

  test("returns Response as-is (no throw, no wrapping)", async () => {
    const res = await engineFetch("/engine/x");
    expect(res).toBeInstanceOf(Response);
    expect(await res.text()).toBe("ok");
  });
});
