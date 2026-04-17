"use client";

import { useEffect, useRef } from "react";
import { signIn } from "next-auth/react";

/**
 * Client-side Telegram Login Widget wrapper.
 *
 * Loads the official widget script with `data-onauth="onTelegramAuth(user)"`
 * and bridges the global callback into next-auth's `signIn("telegram", ...)`.
 * The server-side Credentials `authorize()` verifies the HMAC against
 * TELEGRAM_BOT_TOKEN (lib/telegram-widget.server.ts).
 */
export function TelegramLogin({ botUsername }: { botUsername: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Bridge Telegram's globally-scoped callback into next-auth signIn.
    (window as unknown as {
      onTelegramAuth?: (u: Record<string, string | number>) => void;
    }).onTelegramAuth = async (user) => {
      const payload: Record<string, string> = {};
      for (const [k, v] of Object.entries(user)) payload[k] = String(v);
      await signIn("telegram", { ...payload, redirectTo: "/" });
    };

    // Inject the widget script (idempotent — script has a stable id).
    if (!ref.current) return;
    if (ref.current.querySelector("script")) return;
    const script = document.createElement("script");
    script.async = true;
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.setAttribute("data-telegram-login", botUsername);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    script.setAttribute("data-request-access", "write");
    ref.current.appendChild(script);
  }, [botUsername]);

  return <div ref={ref} data-testid="telegram-widget-mount" />;
}
