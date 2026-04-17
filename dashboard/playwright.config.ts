import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  retries: 0,
  globalSetup: "./tests/e2e/global-setup.ts",
  globalTeardown: "./tests/e2e/global-teardown.ts",
  use: {
    baseURL: process.env.PW_BASE_URL ?? "http://127.0.0.1:8090",
    trace: "retain-on-failure",
  },
  webServer: process.env.PW_EXTERNAL
    ? undefined
    : {
        command: "bun run start",
        port: 8090,
        reuseExistingServer: !process.env.CI,
        env: {
          AUTH_SECRET: "test-secret-insecure",
          DASHBOARD_TOKEN: "test-dash-token",
          TELEGRAM_BOT_TOKEN: "0:dummy",
          ANIMAYA_ENGINE_URL: "http://127.0.0.1:8091",
          OWNER_TELEGRAM_ID: "111111",
        },
      },
});
