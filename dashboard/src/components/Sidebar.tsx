"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/chat", label: "Chat", icon: "💬" },
  { href: "/files", label: "Files", icon: "📁" },
  { href: "/modules", label: "Modules", icon: "🧩" },
  { href: "/settings", label: "Settings", icon: "⚙️" },
  { href: "/stats", label: "Stats", icon: "📊" },
  { href: "/history", label: "History", icon: "🕐" },
  { href: "/logs", label: "Logs", icon: "📋" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 bg-sidebar border-r border-border flex flex-col shrink-0">
      <div className="p-4 border-b border-border">
        <h1 className="text-lg font-bold">Animaya</h1>
        <p className="text-xs text-muted">Personal AI Assistant</p>
      </div>
      <nav className="flex-1 p-2 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname?.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                active
                  ? "bg-accent text-white"
                  : "text-muted hover:bg-card-hover hover:text-foreground"
              }`}
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-4 border-t border-border text-xs text-muted">
        Animaya v0.1.0
      </div>
    </aside>
  );
}
