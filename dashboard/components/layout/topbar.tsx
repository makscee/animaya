import { headers } from "next/headers";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

export async function TopBar() {
  const h = await headers();
  const telegramId = h.get("x-user-telegram-id") ?? "operator";

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-background px-6">
      <div className="text-sm font-medium">Animaya Dashboard</div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Avatar className="h-7 w-7">
            <AvatarFallback>{telegramId.slice(0, 2).toUpperCase()}</AvatarFallback>
          </Avatar>
          <span className="text-sm text-muted-foreground">tg:{telegramId}</span>
        </div>
        <form action="/api/auth/signout" method="post">
          <button
            type="submit"
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Sign out
          </button>
        </form>
      </div>
    </header>
  );
}
