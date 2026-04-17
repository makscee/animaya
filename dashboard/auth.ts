import NextAuth from "next-auth";

import { authConfig } from "./auth.config";
import { readOwnerId } from "@/lib/owner.server";
import { isOwner } from "@/lib/owner-gate.server";

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  callbacks: {
    ...authConfig.callbacks,
    // D-07: reject any Telegram ID that does not match OWNER.md. No
    // first-login-wins fallback — if OWNER.md is missing, signIn fails closed.
    async signIn({ user }) {
      const ownerId = await readOwnerId();
      return isOwner(user?.id ?? null, ownerId);
    },
    async jwt({ token, user }) {
      if (user?.id) token.telegramId = user.id;
      return token;
    },
    async session({ session, token }) {
      if (session.user && typeof token.telegramId === "string") {
        session.user.id = token.telegramId;
      }
      return session;
    },
  },
  cookies: {
    sessionToken: {
      name:
        process.env.NODE_ENV === "production"
          ? "__Secure-authjs.session-token"
          : "authjs.session-token",
      options: {
        httpOnly: true,
        sameSite: "lax",
        path: "/",
        secure: process.env.NODE_ENV === "production",
      },
    },
  },
});
