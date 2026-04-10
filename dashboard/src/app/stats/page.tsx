"use client";

import { useState, useEffect } from "react";

interface StatsData {
  startedAt: string;
  messagesReceived: number;
  messagesSent: number;
  errors: number;
  fileCount: number;
  dataSize: string;
  installedModules: string[];
}

export default function StatsPage() {
  const [stats, setStats] = useState<StatsData | null>(null);

  useEffect(() => {
    fetch("/api/stats")
      .then((r) => r.json())
      .then(setStats)
      .catch(() => {});

    const interval = setInterval(() => {
      fetch("/api/stats")
        .then((r) => r.json())
        .then(setStats)
        .catch(() => {});
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col h-full">
      <header className="p-4 border-b border-border">
        <h2 className="text-lg font-semibold">Stats & Usage</h2>
      </header>

      <div className="flex-1 overflow-y-auto p-4">
        {!stats ? (
          <div className="text-center text-muted py-8">Loading stats...</div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 max-w-3xl">
            <StatCard label="Messages Received" value={stats.messagesReceived} icon="📨" />
            <StatCard label="Messages Sent" value={stats.messagesSent} icon="📤" />
            <StatCard label="Errors" value={stats.errors} icon="⚠️" variant={stats.errors > 0 ? "error" : "default"} />
            <StatCard label="Files" value={stats.fileCount} icon="📁" />
            <StatCard label="Data Size" value={stats.dataSize} icon="💾" />
            <StatCard label="Uptime Since" value={stats.startedAt} icon="⏱️" />
            <div className="sm:col-span-2 lg:col-span-3 bg-card border border-border rounded-xl p-4">
              <h3 className="text-sm font-medium mb-2">Installed Modules</h3>
              <div className="flex flex-wrap gap-2">
                {stats.installedModules.length > 0 ? (
                  stats.installedModules.map((m) => (
                    <span key={m} className="text-xs bg-accent/20 text-accent px-2 py-1 rounded-full">
                      {m}
                    </span>
                  ))
                ) : (
                  <span className="text-sm text-muted">No modules installed yet</span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  variant = "default",
}: {
  label: string;
  value: string | number;
  icon: string;
  variant?: "default" | "error";
}) {
  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <div className="flex items-center gap-2 mb-1">
        <span>{icon}</span>
        <span className="text-xs text-muted">{label}</span>
      </div>
      <div className={`text-2xl font-bold ${variant === "error" ? "text-error" : ""}`}>
        {value}
      </div>
    </div>
  );
}
