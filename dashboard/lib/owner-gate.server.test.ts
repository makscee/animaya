import { describe, test, expect } from "bun:test";
import { isOwner } from "./owner-gate.server";

describe("isOwner (D-07 owner gate, no-fallback)", () => {
  test("accepts matching ids", () => {
    expect(isOwner("123", "123")).toBe(true);
  });

  test("rejects when OWNER.md missing (ownerId null)", () => {
    expect(isOwner("123", null)).toBe(false);
  });

  test("rejects mismatched ids", () => {
    expect(isOwner("123", "999")).toBe(false);
  });

  test("rejects when provided id missing", () => {
    expect(isOwner(null, "123")).toBe(false);
    expect(isOwner("", "123")).toBe(false);
  });
});
