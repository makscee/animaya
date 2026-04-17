import { TelegramLogin } from "./telegram-login";

/**
 * Login page — embeds the Telegram Login Widget and hands off to
 * next-auth v5 Credentials provider (id: "telegram").
 *
 * Integration choice (documented per plan 13-05 Task 1):
 *   next-auth@5.0.0-beta.31 requires a POSTed CSRF token on
 *   /api/auth/callback/credentials, which the Widget's `data-auth-url`
 *   flow cannot provide (it GET-redirects with query params). So we
 *   use the client-callback variant: Telegram calls a global
 *   `onTelegramAuth(user)` after user consents; our wrapper captures
 *   the payload and invokes `signIn("telegram", payload, { redirect })`,
 *   which handles CSRF internally.
 */
export default function LoginPage() {
  const username = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME;
  return (
    <main className="flex min-h-screen items-center justify-center p-8">
      <div className="flex flex-col items-center gap-6 rounded-xl border border-border bg-card p-8 shadow-xs">
        <h1 className="text-2xl font-semibold">Sign in to Animaya</h1>
        {username ? (
          <TelegramLogin botUsername={username} />
        ) : (
          <p className="max-w-sm text-center text-sm text-muted-foreground">
            Telegram widget unavailable — set
            {" "}
            <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">
              NEXT_PUBLIC_TELEGRAM_BOT_USERNAME
            </code>
            {" "}
            in the dashboard environment.
          </p>
        )}
      </div>
    </main>
  );
}
