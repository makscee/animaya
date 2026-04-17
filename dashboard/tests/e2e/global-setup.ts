import { startMockEngine } from "./_mock-engine";
import type { Server } from "node:http";

let server: Server | null = null;

async function globalSetup() {
  server = await startMockEngine(8091);
  // Stash teardown on process so `global-teardown.ts` can close it.
  (globalThis as unknown as { __ANIMAYA_MOCK_ENGINE?: Server }).__ANIMAYA_MOCK_ENGINE =
    server;
  return async () => {
    server?.close();
  };
}

export default globalSetup;
