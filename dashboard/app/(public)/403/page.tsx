import { auth, signOut } from "@/auth";

export default async function ForbiddenPage() {
  const session = await auth();
  const telegramId =
    (session?.user as { id?: string } | undefined)?.id ?? "unknown";
  return (
    <main className="flex min-h-screen items-center justify-center p-8">
      <div className="flex max-w-md flex-col gap-4 rounded-xl border border-destructive/40 bg-card p-8 text-center shadow-xs">
        <h1 className="text-2xl font-semibold text-destructive">
          403 — Not Authorized
        </h1>
        <p className="text-sm text-muted-foreground">
          Telegram user{" "}
          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
            {telegramId}
          </code>{" "}
          is not the Animaya owner.
        </p>
        <form
          action={async () => {
            "use server";
            await signOut({ redirectTo: "/login" });
          }}
        >
          <button type="submit" className="text-sm underline">
            Sign out
          </button>
        </form>
      </div>
    </main>
  );
}
