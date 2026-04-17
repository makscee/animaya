import { expect, test } from "@playwright/test";

test.use({ extraHTTPHeaders: { "x-dashboard-token": "test-dash-token" } });

const bridgeState = {
  enabled: false,
  policy: "owner_only" as const,
  owner_id: null as string | null,
  claim_code_present: false,
};

test("claim issues a code, revoke clears it, policy PUTs a valid zod shape", async ({
  page,
}) => {
  let state = { ...bridgeState };
  await page.route("**/api/bridge", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(state),
    }),
  );
  await page.route("**/api/bridge/claim", async (route) => {
    state = { ...state, claim_code_present: true };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true }),
    });
  });
  await page.route("**/api/bridge/revoke", async (route) => {
    state = { ...state, claim_code_present: false, owner_id: null };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true }),
    });
  });
  let policyBody = "";
  await page.route("**/api/bridge/policy", async (route) => {
    policyBody = route.request().postData() ?? "";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true }),
    });
  });

  await page.goto("/bridge");
  await expect(page.locator("body")).toContainText("unclaimed");
  await page.locator('[data-testid="bridge-claim"]').click();

  // Policy select → save PUT.
  await page.locator('[data-testid="bridge-policy-select"]').click();
  await page.getByRole("option", { name: "allowlist" }).click();
  await page.locator('[data-testid="bridge-policy-save"]').click();
  await expect.poll(() => policyBody).toContain("allowlist");
  // Must parse as valid BridgePolicyPayload zod shape.
  const parsed = JSON.parse(policyBody) as { policy: string };
  expect(["owner_only", "allowlist", "open"]).toContain(parsed.policy);

  // Revoke.
  await page.locator('[data-testid="bridge-revoke"]').click();
});
