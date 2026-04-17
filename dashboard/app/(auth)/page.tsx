import Link from "next/link";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

// Server-rendered landing surface. Live counters (messages, modules installed)
// will be wired in Plan 06 once the legacy Jinja home is retired and engine
// `/engine/status` is stable enough to block SSR on.
export const dynamic = "force-dynamic";

const QUICK_LINKS: { href: string; title: string; desc: string }[] = [
  {
    href: "/chat",
    title: "Chat",
    desc: "Unified conversation with your Animaya + Hub tree browser.",
  },
  {
    href: "/modules",
    title: "Modules",
    desc: "Install, uninstall, and configure pluggable capabilities.",
  },
  {
    href: "/bridge",
    title: "Bridge",
    desc: "Claim your Telegram bot, rotate codes, manage access policy.",
  },
];

export default function HomePage() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold">Animaya</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Personal AI assistant — Telegram bridge + Hub memory + installable
          modules.
        </p>
      </div>
      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {QUICK_LINKS.map((link) => (
          <Link key={link.href} href={link.href} className="group">
            <Card className="h-full transition-colors group-hover:border-primary/50">
              <CardHeader>
                <CardTitle>{link.title}</CardTitle>
                <CardDescription>{link.desc}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </section>
    </div>
  );
}
