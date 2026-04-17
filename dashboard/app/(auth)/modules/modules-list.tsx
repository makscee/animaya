"use client";

import Link from "next/link";
import { toast } from "sonner";
import useSWR from "swr";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type Module = {
  name: string;
  title?: string;
  description?: string;
  installed: boolean;
  // bot_token etc. are redacted server-side by lib/redact.server.ts (T-13-44)
};

type ModulesResponse = { modules: Module[] };

const fetcher = (url: string) => fetch(url).then((r) => r.json());

function readCsrf(): string {
  if (typeof document === "undefined") return "";
  const m = document.cookie.match(/(?:^|;\s*)an-csrf=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}

export function ModulesList() {
  const { data, isLoading, error, mutate } = useSWR<ModulesResponse>(
    "/api/modules",
    fetcher,
  );

  const act = async (name: string, action: "install" | "uninstall") => {
    const res = await fetch(`/api/modules/${name}/${action}`, {
      method: "POST",
      headers: { "x-csrf-token": readCsrf() },
    });
    if (!res.ok) {
      toast.error(`Failed to ${action} ${name}`);
      return;
    }
    toast.success(`${action === "install" ? "Installed" : "Uninstalled"} ${name}`);
    void mutate();
  };

  if (isLoading) return <div className="text-muted-foreground">Loading…</div>;
  if (error || !data)
    return <div className="text-destructive">Failed to load modules</div>;

  return (
    <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {data.modules.map((mod) => (
        <Card key={mod.name} data-testid={`module-card-${mod.name}`}>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <Link
                href={`/modules/${mod.name}`}
                className="hover:underline"
              >
                {mod.title ?? mod.name}
              </Link>
              <span
                className={
                  mod.installed
                    ? "rounded bg-primary/20 px-2 py-0.5 text-xs text-primary"
                    : "rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                }
              >
                {mod.installed ? "installed" : "available"}
              </span>
            </CardTitle>
            {mod.description ? (
              <CardDescription>{mod.description}</CardDescription>
            ) : null}
          </CardHeader>
          <CardContent className="flex gap-2">
            {mod.installed ? (
              <Button
                variant="outline"
                onClick={() => act(mod.name, "uninstall")}
                data-testid={`module-uninstall-${mod.name}`}
              >
                Uninstall
              </Button>
            ) : (
              <Button
                onClick={() => act(mod.name, "install")}
                data-testid={`module-install-${mod.name}`}
              >
                Install
              </Button>
            )}
            <Link
              href={`/modules/${mod.name}`}
              className="text-sm text-muted-foreground hover:underline"
            >
              Configure →
            </Link>
          </CardContent>
        </Card>
      ))}
    </section>
  );
}
