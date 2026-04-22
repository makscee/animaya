// Locks A1/A3 assumption from 14-RESEARCH.md — next-auth/jwt encode()/decode()
// with matching salt is the Auth.js v5 path getToken() uses. If this test fails,
// Plan 02 verifier strategy must fall back to jose directly.

import { describe, test, expect } from "bun:test";
import { encode, decode } from "next-auth/jwt";

const SECRET = "a".repeat(64); // matches typical AUTH_SECRET length
const PROD_SALT = "__Secure-authjs.session-token";
const DEV_SALT = "authjs.session-token";
const MAX_AGE = 60 * 60 * 8;

describe("next-auth/jwt encode/decode roundtrip", () => {
  test("encode with prod salt → decode with prod salt yields same telegramId+sub+name", async () => {
    const jwt = await encode({
      token: {
        sub: "111111",
        telegramId: "111111",
        name: "testuser",
        src: "voidnet",
      },
      secret: SECRET,
      maxAge: MAX_AGE,
      salt: PROD_SALT,
    });
    expect(typeof jwt).toBe("string");
    expect(jwt.length).toBeGreaterThan(0);

    const decoded = await decode({ token: jwt, secret: SECRET, salt: PROD_SALT });
    expect(decoded?.sub).toBe("111111");
    expect((decoded as { telegramId?: string } | null)?.telegramId).toBe("111111");
    expect((decoded as { name?: string } | null)?.name).toBe("testuser");
  });

  test("encode with mismatched salt → decode fails (Pitfall 1 guard)", async () => {
    // Auth.js v5 `decode()` throws a JWEDecryptionFailed when the salt used to
    // derive the encryption key doesn't match. Either throw or null-return is
    // acceptable — both prove Pitfall 1 is covered (wrong salt cannot decrypt).
    const jwt = await encode({
      token: {
        sub: "111111",
        telegramId: "111111",
        name: "testuser",
        src: "voidnet",
      },
      secret: SECRET,
      maxAge: MAX_AGE,
      salt: DEV_SALT,
    });

    let decoded: unknown = "not-set";
    let threw = false;
    try {
      decoded = await decode({ token: jwt, secret: SECRET, salt: PROD_SALT });
    } catch {
      threw = true;
    }
    // Must either throw, or return null — but must NOT successfully decode.
    expect(threw || decoded === null).toBe(true);
  });
});
