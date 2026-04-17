import { describe, test, expect } from "bun:test";
import { sanitizeErrorMessage } from "./redact.server";

describe("sanitizeErrorMessage", () => {
  test("redacts telegram bot tokens", () => {
    const msg = "Error: bad token 1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ-_abcdefghi failed";
    const out = sanitizeErrorMessage(msg);
    expect(out).toContain("[REDACTED_TG_TOKEN]");
    expect(out).not.toContain("1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ");
  });

  test("redacts Claude OAuth tokens", () => {
    const msg = "Auth error with sk-ant-oat01-abcDEFghiJKLmnoPQRstuVWXyz_1234 please retry";
    const out = sanitizeErrorMessage(msg);
    expect(out).toContain("[REDACTED_OAUTH]");
    expect(out).not.toContain("sk-ant-oat01-abcDEFghi");
  });

  test("redacts long hex blobs", () => {
    const msg = "hash mismatch: abcdef0123456789abcdef0123456789abcdef01";
    const out = sanitizeErrorMessage(msg);
    expect(out).toContain("[REDACTED_HEX]");
    expect(out).not.toContain("abcdef0123456789abcdef0123456789");
  });
});
