import Link from "next/link";
import { NAV_ITEMS } from "./nav-items";

export function Sidebar() {
  return (
    <aside className="flex h-screen w-56 shrink-0 flex-col gap-1 border-r border-border bg-sidebar p-4">
      <div className="mb-4 px-2 text-sm font-semibold">Animaya</div>
      <nav className="flex flex-col gap-0.5">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="rounded-md px-2 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
