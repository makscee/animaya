import type { NextAuthConfig } from "next-auth";
import Credentials from "next-auth/providers/credentials";

import { verifyTelegramWidget } from "@/lib/telegram-widget.server";

export const authConfig = {
  session: { strategy: "jwt", maxAge: 60 * 60 * 8 }, // 8h
  trustHost: true, // required behind Caddy reverse proxy
  pages: { signIn: "/login", error: "/login" },
  providers: [
    Credentials({
      id: "telegram",
      name: "Telegram",
      // Telegram Login Widget posts id/first_name/username/photo_url/auth_date/hash.
      // We accept anything and validate via the HMAC port.
      credentials: {},
      async authorize(raw) {
        const token = process.env.TELEGRAM_BOT_TOKEN;
        if (!token) return null;
        const payload = verifyTelegramWidget(raw, token);
        if (!payload) return null;
        return {
          id: String(payload.id),
          name: payload.first_name ?? payload.username ?? "telegram-user",
        };
      },
    }),
  ],
  callbacks: {
    // authorized() is consulted by the auth() middleware wrapper.
    // Owner enforcement lives in middleware.ts + signIn callback (auth.ts);
    // this just asserts "has a session".
    authorized: ({ auth }) => !!auth,
  },
} satisfies NextAuthConfig;
