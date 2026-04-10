"use client";

import { useState, useEffect } from "react";

interface Session {
  id: string;
  lastMessage: string;
  timestamp: string;
  messageCount: number;
}

export default function HistoryPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);

  useEffect(() => {
    fetch("/api/chat/history")
      .then((r) => r.json())
      .then((data) => setSessions(data.sessions || []))
      .catch(() => {});
  }, []);

  async function loadSession(id: string) {
    setSelected(id);
    try {
      const res = await fetch(`/api/chat/history?session=${id}`);
      const data = await res.json();
      setMessages(data.messages || []);
    } catch {
      setMessages([]);
    }
  }

  return (
    <div className="flex h-full">
      <div className="w-64 border-r border-border overflow-y-auto">
        <header className="p-4 border-b border-border">
          <h2 className="text-lg font-semibold">History</h2>
        </header>
        {sessions.length === 0 ? (
          <div className="p-4 text-sm text-muted">No conversations yet</div>
        ) : (
          sessions.map((s) => (
            <button
              key={s.id}
              onClick={() => loadSession(s.id)}
              className={`w-full text-left p-3 border-b border-border text-sm hover:bg-card-hover ${
                selected === s.id ? "bg-card" : ""
              }`}
            >
              <div className="font-medium truncate">{s.lastMessage || "New conversation"}</div>
              <div className="text-xs text-muted mt-0.5">
                {s.timestamp} · {s.messageCount} messages
              </div>
            </button>
          ))
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {!selected ? (
          <div className="flex items-center justify-center h-full text-muted">
            Select a conversation to view
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center text-muted py-8">No messages in this session</div>
        ) : (
          <div className="space-y-3 max-w-2xl">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[75%] rounded-xl px-4 py-2.5 text-sm ${
                    msg.role === "user" ? "bg-accent text-white" : "bg-card border border-border"
                  }`}
                >
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
