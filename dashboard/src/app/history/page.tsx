"use client";

import { useState, useEffect } from "react";

interface HistoryMessage {
  role: string;
  content: string;
  tools: string[];
  source: string;
  timestamp: string;
}

export default function HistoryPage() {
  const [messages, setMessages] = useState<HistoryMessage[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/chat/history?limit=200")
      .then((r) => r.json())
      .then((data) => setMessages(data.messages || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered =
    filter === "all"
      ? messages
      : messages.filter((m) => m.source === filter);

  const sources = [...new Set(messages.map((m) => m.source))];

  return (
    <div className="flex flex-col h-full">
      <header className="p-4 border-b border-border flex items-center gap-3">
        <h2 className="text-lg font-semibold">Conversation History</h2>
        <span className="text-xs text-muted">{messages.length} messages</span>
        <div className="flex-1" />
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="bg-card border border-border rounded px-2 py-1 text-sm"
        >
          <option value="all">All sources</option>
          {sources.map((s) => (
            <option key={s} value={s}>
              {s === "telegram" ? "Telegram" : s === "web" ? "Web Chat" : s}
            </option>
          ))}
        </select>
      </header>

      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="text-center text-muted py-8">Loading history...</div>
        ) : filtered.length === 0 ? (
          <div className="text-center text-muted py-8">
            No messages yet. Chat with your bot via Telegram or the Chat tab.
          </div>
        ) : (
          <div className="space-y-3 max-w-2xl mx-auto">
            {filtered.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[75%] rounded-xl px-4 py-2.5 text-sm ${
                    msg.role === "user"
                      ? "bg-accent text-white"
                      : "bg-card border border-border"
                  }`}
                >
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                  <div className="flex items-center gap-2 mt-1.5 text-xs opacity-60">
                    <span>{msg.source === "telegram" ? "📱" : "💻"}</span>
                    <span>{new Date(msg.timestamp).toLocaleString()}</span>
                  </div>
                  {msg.tools && msg.tools.length > 0 && (
                    <details className="mt-1.5 pt-1.5 border-t border-border/50">
                      <summary className="text-xs text-muted cursor-pointer">
                        {msg.tools.length} tool{msg.tools.length !== 1 ? "s" : ""} used
                      </summary>
                      <ul className="mt-1 text-xs text-muted space-y-0.5">
                        {msg.tools.map((t, j) => (
                          <li key={j}>• {t}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
