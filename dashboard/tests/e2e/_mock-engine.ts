/**
 * Tiny loopback FastAPI stand-in used by Playwright specs.
 *
 * Spun up by `global-setup.ts` on 127.0.0.1:8091 to mimic the Phase 13-04
 * engine surface — ONLY the endpoints the Next.js route handlers (Plan 13-03)
 * would forward to. Because Plan 13-03 isn't merged on this branch yet, the
 * specs stub Next.js API routes via `page.route()` rather than hitting this
 * sidecar; the sidecar is started anyway so the build's engineFetch path
 * resolves if the test runner ever calls it directly (D-01 loopback check).
 */
import { createServer, type Server } from "node:http";

type Handler = (
  req: import("node:http").IncomingMessage,
  res: import("node:http").ServerResponse,
) => void;

const json = (res: import("node:http").ServerResponse, code: number, body: unknown) => {
  res.writeHead(code, { "content-type": "application/json" });
  res.end(JSON.stringify(body));
};

const routes: Record<string, Handler> = {
  "GET /engine/status": (_req, res) => json(res, 200, { ok: true, version: "test" }),
  "GET /engine/modules": (_req, res) =>
    json(res, 200, {
      modules: [
        { name: "audio", title: "Audio", description: "Whisper STT", installed: true },
        { name: "image", title: "Image Gen", description: "Gemini images", installed: false },
      ],
    }),
};

export function startMockEngine(port = 8091): Promise<Server> {
  return new Promise((resolve) => {
    const server = createServer((req, res) => {
      const key = `${req.method} ${req.url?.split("?")[0]}`;
      const h = routes[key];
      if (h) return h(req, res);
      json(res, 404, { error: "not found", key });
    });
    server.listen(port, "127.0.0.1", () => resolve(server));
  });
}
