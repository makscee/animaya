import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { promises as fs } from "node:fs";
import * as path from "node:path";
import * as os from "node:os";

import { safeResolve, listDir, getHubRoot } from "./hub-tree.server";

let tmpRoot: string;
let outsideDir: string;

beforeEach(async () => {
  tmpRoot = await fs.mkdtemp(path.join(os.tmpdir(), "animaya-hub-"));
  outsideDir = await fs.mkdtemp(path.join(os.tmpdir(), "animaya-outside-"));
  process.env.HUB_ROOT_OVERRIDE = tmpRoot;

  // Fixture tree:
  //   <root>/knowledge/notes.md
  //   <root>/.git/hooks/pre-commit
  //   <root>/.env
  //   <root>/a/file.txt
  //   <root>/b/ (empty dir)
  //   <root>/.hidden-dir/inside
  await fs.mkdir(path.join(tmpRoot, "knowledge"));
  await fs.writeFile(path.join(tmpRoot, "knowledge/notes.md"), "hi");
  await fs.mkdir(path.join(tmpRoot, ".git/hooks"), { recursive: true });
  await fs.writeFile(path.join(tmpRoot, ".git/hooks/pre-commit"), "#!/bin/sh\n");
  await fs.writeFile(path.join(tmpRoot, ".env"), "SECRET=shh");
  await fs.mkdir(path.join(tmpRoot, "a"));
  await fs.writeFile(path.join(tmpRoot, "a/file.txt"), "x");
  await fs.mkdir(path.join(tmpRoot, "b"));
  await fs.mkdir(path.join(tmpRoot, ".hidden-dir"));
  await fs.writeFile(path.join(tmpRoot, ".hidden-dir/inside"), "y");
});

afterEach(async () => {
  delete process.env.HUB_ROOT_OVERRIDE;
  await fs.rm(tmpRoot, { recursive: true, force: true });
  await fs.rm(outsideDir, { recursive: true, force: true });
});

describe("safeResolve", () => {
  test("empty string resolves to HUB_ROOT", async () => {
    const resolved = await safeResolve("");
    const realRoot = await fs.realpath(getHubRoot());
    expect(resolved).toBe(realRoot);
  });

  test("knowledge resolves inside HUB_ROOT", async () => {
    const resolved = await safeResolve("knowledge");
    const realRoot = await fs.realpath(getHubRoot());
    expect(resolved).toBe(path.join(realRoot, "knowledge"));
  });

  test("traversal with ../../etc/passwd throws", async () => {
    await expect(safeResolve("../../../etc/passwd")).rejects.toThrow();
  });

  test(".git/hooks/pre-commit throws (DENY)", async () => {
    await expect(safeResolve(".git/hooks/pre-commit")).rejects.toThrow();
  });

  test(".env throws (DENY_PREFIX)", async () => {
    await expect(safeResolve(".env")).rejects.toThrow();
  });

  test("symlink escape throws", async () => {
    // Create a symlink inside HUB_ROOT that points to a dir outside HUB_ROOT.
    const linkPath = path.join(tmpRoot, "escape");
    await fs.symlink(outsideDir, linkPath, "dir");
    // Resolving the link should surface the canonical outside-root path and
    // be rejected by the prefix-check.
    await expect(safeResolve("escape")).rejects.toThrow();
  });
});

describe("listDir", () => {
  test("omits dotfiles by default (showHidden=false)", async () => {
    const entries = await listDir("", { showHidden: false });
    const names = entries.map((e) => e.name);
    expect(names).toContain("knowledge");
    expect(names).toContain("a");
    expect(names).toContain("b");
    expect(names).not.toContain(".env");
    expect(names).not.toContain(".git");
    expect(names).not.toContain(".hidden-dir");
  });

  test("includes non-sensitive dotfiles when showHidden=true but still denies DENY + DENY_PREFIX", async () => {
    const entries = await listDir("", { showHidden: true });
    const names = entries.map((e) => e.name);
    expect(names).toContain(".hidden-dir");
    expect(names).not.toContain(".env"); // DENY_PREFIX always hidden
    expect(names).not.toContain(".git"); // DENY always hidden
  });

  test("returns entries sorted dir-first then name", async () => {
    const entries = await listDir("", { showHidden: false });
    // Expected non-hidden ordering: dirs (a, b, knowledge) then files.
    const types = entries.map((e) => e.type);
    const firstFileIndex = types.indexOf("file");
    if (firstFileIndex !== -1) {
      // No "dir" may appear after the first "file".
      for (let i = firstFileIndex; i < types.length; i++) {
        expect(types[i]).toBe("file");
      }
    }
    const dirNames = entries.filter((e) => e.type === "dir").map((e) => e.name);
    const sortedDirs = [...dirNames].sort((a, b) => a.localeCompare(b));
    expect(dirNames).toEqual(sortedDirs);
  });
});
