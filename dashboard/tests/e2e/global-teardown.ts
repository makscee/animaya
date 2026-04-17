import type { Server } from "node:http";

async function globalTeardown() {
  const server = (globalThis as unknown as { __ANIMAYA_MOCK_ENGINE?: Server })
    .__ANIMAYA_MOCK_ENGINE;
  await new Promise<void>((resolve) => {
    if (!server) return resolve();
    server.close(() => resolve());
  });
}

export default globalTeardown;
