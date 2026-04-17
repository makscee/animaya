import { expect, test } from "@playwright/test";

/**
 * DASH-02: /chat streams assistant frames via SSE-over-POST; tool_use /
 * tool_result frames render as inline Cards between text frames.
 *
 * We use `page.route()` to stub /api/chat/stream with a deterministic
 * event sequence. The hub tree call is also stubbed to a minimal root.
 */

test.use({ extraHTTPHeaders: { "x-dashboard-token": "test-dash-token" } });

function sseFrame(obj: unknown): string {
  return `data: ${JSON.stringify(obj)}\n\n`;
}

test("chat renders text and tool_use Cards inline; heartbeats hidden", async ({
  page,
}) => {
  // Stub hub tree.
  await page.route("**/api/hub/tree**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        root: { name: "/", path: "", type: "dir", children: [] },
      }),
    }),
  );

  // Stub SSE stream with text → tool_use → tool_result → text → end.
  await page.route("**/api/chat/stream", async (route) => {
    const body =
      ":ping\n\n" +
      sseFrame({ type: "text", content: "Hello!" }) +
      sseFrame({ type: "tool_use", tool: "Bash", input: { cmd: "ls" } }) +
      sseFrame({ type: "tool_result", tool: "Bash", output: "file1\nfile2" }) +
      sseFrame({ type: "text", content: "Done." }) +
      sseFrame({ type: "end" });
    await route.fulfill({
      status: 200,
      headers: { "content-type": "text/event-stream" },
      body,
    });
  });

  await page.goto("/chat");
  await page.locator('[data-testid="chat-input"]').fill("hi");
  await page.locator('[data-testid="chat-send"]').click();

  await expect(page.locator('[data-testid="chat-tool-use"]')).toBeVisible();
  await expect(page.locator('[data-testid="chat-tool-result"]')).toBeVisible();
  const texts = page.locator('[data-testid="chat-text"]');
  await expect(texts.first()).toContainText(/Hello/);
  // No `:ping` heartbeat ever rendered as a message.
  await expect(page.locator("body")).not.toContainText(":ping");
});

test("chat reconnects after forced stream close (retries once)", async ({
  page,
}) => {
  await page.route("**/api/hub/tree**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        root: { name: "/", path: "", type: "dir", children: [] },
      }),
    }),
  );
  let attempts = 0;
  await page.route("**/api/chat/stream", async (route) => {
    attempts += 1;
    if (attempts === 1) {
      // Fail the first attempt hard to exercise the backoff/retry path.
      await route.abort();
      return;
    }
    await route.fulfill({
      status: 200,
      headers: { "content-type": "text/event-stream" },
      body: sseFrame({ type: "text", content: "retry-ok" }) + sseFrame({ type: "end" }),
    });
  });

  await page.goto("/chat");
  await page.locator('[data-testid="chat-input"]').fill("retry?");
  await page.locator('[data-testid="chat-send"]').click();
  await expect(page.locator('[data-testid="chat-text"]')).toContainText(
    /retry-ok/,
    { timeout: 15_000 },
  );
  expect(attempts).toBeGreaterThanOrEqual(2);
});
