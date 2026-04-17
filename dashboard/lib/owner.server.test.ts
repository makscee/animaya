import { describe, test, expect, beforeEach, afterEach } from "bun:test";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";

import { readOwnerId, _resetOwnerCache } from "./owner.server";

let tmpDir: string;
let ownerPath: string;

beforeEach(async () => {
  tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "animaya-owner-"));
  ownerPath = path.join(tmpDir, "OWNER.md");
  process.env.OWNER_MD_PATH = ownerPath;
  _resetOwnerCache();
});

afterEach(async () => {
  await fs.rm(tmpDir, { recursive: true, force: true });
  delete process.env.OWNER_MD_PATH;
  _resetOwnerCache();
});

describe("readOwnerId", () => {
  test("returns telegram_id string when OWNER.md has `telegram_id: 12345`", async () => {
    await fs.writeFile(
      ownerPath,
      "# Owner\n\ntelegram_id: 12345\nusername: alice\n",
    );
    expect(await readOwnerId()).toBe("12345");
  });

  test("returns null when OWNER.md missing", async () => {
    expect(await readOwnerId()).toBeNull();
  });

  test("returns null when OWNER.md has no telegram_id line", async () => {
    await fs.writeFile(ownerPath, "# Owner\n\nusername: alice\n");
    expect(await readOwnerId()).toBeNull();
  });

  test("second call uses cache (unaffected by fs change)", async () => {
    await fs.writeFile(ownerPath, "telegram_id: 77\n");
    const first = await readOwnerId();
    // Remove the file; cached result should still be returned.
    await fs.rm(ownerPath);
    const second = await readOwnerId();
    expect(first).toBe("77");
    expect(second).toBe("77");
  });
});
