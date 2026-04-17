import { expect, test } from "@playwright/test";

/**
 * DASH-03: tree hides dotfiles by default; toggle persists via
 * localStorage; clicking a file loads `/api/hub/file` into the
 * right-pane viewer.
 */

test.use({ extraHTTPHeaders: { "x-dashboard-token": "test-dash-token" } });

const treeBody = {
  root: {
    name: "/",
    path: "",
    type: "dir" as const,
    children: [
      {
        name: "OWNER.md",
        path: "OWNER.md",
        type: "file" as const,
      },
      {
        name: ".git",
        path: ".git",
        type: "dir" as const,
        children: [],
      },
      {
        name: "spaces",
        path: "spaces",
        type: "dir" as const,
        children: [
          {
            name: "project.md",
            path: "spaces/project.md",
            type: "file" as const,
          },
        ],
      },
    ],
  },
};

test("dotfiles hidden by default, shown after toggle (persists via localStorage)", async ({
  page,
}) => {
  await page.route("**/api/chat/stream", (route) => route.abort());
  await page.route("**/api/hub/tree**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(treeBody),
    }),
  );

  await page.goto("/chat");
  const tree = page.locator('[data-testid="hub-tree"]');
  await expect(tree).toBeVisible();
  await expect(tree).toContainText("OWNER.md");
  await expect(tree).not.toContainText(".git");

  await page.locator('[data-testid="hub-tree-toggle-hidden"]').click();
  await expect(tree).toContainText(".git");

  // Verify localStorage preference.
  const stored = await page.evaluate(() =>
    window.localStorage.getItem("animaya.treeShowHidden"),
  );
  expect(stored).toBe("true");

  // Reload → preference persists.
  await page.reload();
  await expect(page.locator('[data-testid="hub-tree"]')).toContainText(".git");
});

test("clicking a file loads /api/hub/file into the right-pane viewer", async ({
  page,
}) => {
  await page.route("**/api/chat/stream", (route) => route.abort());
  await page.route("**/api/hub/tree**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(treeBody),
    }),
  );
  await page.route("**/api/hub/file**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ content: "# Owner\n\n- telegram_id: 111111\n" }),
    }),
  );

  await page.goto("/chat");
  // Ensure localStorage is clean (prev test may have set showHidden=true).
  await page.evaluate(() => window.localStorage.clear());
  await page.reload();
  await page.locator('[data-testid="hub-tree-file"]', { hasText: "OWNER.md" }).click();
  await expect(page.locator('[data-testid="hub-viewer"]')).toContainText(
    "telegram_id",
  );
});
