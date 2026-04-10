"use client";

import { useState, useEffect, useRef } from "react";

interface LogEntry {
  timestamp: string;
  level: string;
  logger: string;
  message: string;
}

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<string>("ALL");
  const [autoScroll, setAutoScroll] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, [filter]);

  useEffect(() => {
    if (autoScroll) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs, autoScroll]);

  async function fetchLogs() {
    try {
      const level = filter === "ALL" ? "" : filter;
      const res = await fetch(`/api/logs?level=${level}&limit=200`);
      const data = await res.json();
      setLogs(data.entries || []);
    } catch {
      // ignore
    }
  }

  const errorCount = logs.filter((l) => l.level === "ERROR").length;

  return (
    <div className="flex flex-col h-full">
      <header className="p-4 border-b border-border flex items-center gap-4">
        <h2 className="text-lg font-semibold">Logs</h2>
        {errorCount > 0 && (
          <span className="text-xs bg-error/20 text-error px-2 py-1 rounded-full">
            {errorCount} errors
          </span>
        )}
        <div className="flex-1" />
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="bg-card border border-border rounded px-2 py-1 text-sm"
        >
          <option value="ALL">All levels</option>
          <option value="ERROR">Errors only</option>
          <option value="WARNING">Warnings+</option>
          <option value="INFO">Info+</option>
        </select>
        <label className="flex items-center gap-1.5 text-sm text-muted">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
            className="rounded"
          />
          Auto-scroll
        </label>
      </header>

      <div className="flex-1 overflow-y-auto font-mono text-xs">
        {logs.length === 0 ? (
          <div className="p-8 text-center text-muted">No logs available</div>
        ) : (
          logs.map((entry, i) => (
            <div
              key={i}
              className={`px-4 py-1 border-b border-border/50 flex gap-3 ${
                entry.level === "ERROR"
                  ? "bg-error/10"
                  : entry.level === "WARNING"
                    ? "bg-warning/10"
                    : ""
              }`}
            >
              <span className="text-muted shrink-0">{entry.timestamp}</span>
              <span
                className={`w-12 shrink-0 font-bold ${
                  entry.level === "ERROR"
                    ? "text-error"
                    : entry.level === "WARNING"
                      ? "text-warning"
                      : "text-muted"
                }`}
              >
                {entry.level}
              </span>
              <span className="text-muted shrink-0">{entry.logger}</span>
              <span className="break-all">{entry.message}</span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
