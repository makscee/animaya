"use client";

import { useState, useRef, useEffect, useCallback } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  tools?: string[];
  timestamp: string;
}

const STORAGE_KEY = "animaya-chat-messages";

function loadMessages(): Message[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveMessages(messages: Message[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  } catch {
    // storage full — trim old messages
    const trimmed = messages.slice(-50);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  }
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [activeTools, setActiveTools] = useState<string[]>([]);
  const [showTools, setShowTools] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const toolsRef = useRef<string[]>([]);

  // Load from localStorage on mount
  useEffect(() => {
    setMessages(loadMessages());
  }, []);

  // Save to localStorage on change
  useEffect(() => {
    if (messages.length > 0) saveMessages(messages);
  }, [messages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamText]);

  const addMessage = useCallback((msg: Message) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");

    const userMsg: Message = {
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };
    addMessage(userMsg);
    setLoading(true);
    setStreamText("");
    setActiveTools([]);
    toolsRef.current = [];

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      if (!res.ok) throw new Error(`API error: ${res.status}`);

      const es = new EventSource("/api/chat/stream");
      es.addEventListener("token", (e) => {
        const data = JSON.parse(e.data);
        setStreamText((prev) => prev + data.text);
      });
      es.addEventListener("tool", (e) => {
        const data = JSON.parse(e.data);
        toolsRef.current = [...toolsRef.current, data.name];
        setActiveTools([...toolsRef.current]);
      });
      es.addEventListener("done", (e) => {
        const data = JSON.parse(e.data);
        es.close();
        setStreamText("");
        const assistantMsg: Message = {
          role: "assistant",
          content: data.fullText,
          tools: toolsRef.current,
          timestamp: new Date().toISOString(),
        };
        addMessage(assistantMsg);
        setLoading(false);
        setActiveTools([]);
        toolsRef.current = [];
      });
      es.addEventListener("error", () => {
        es.close();
        setStreamText("");
        addMessage({
          role: "assistant",
          content: "Connection lost. Please try again.",
          timestamp: new Date().toISOString(),
        });
        setLoading(false);
      });
    } catch {
      addMessage({
        role: "assistant",
        content: "Failed to send message. Is the bot running?",
        timestamp: new Date().toISOString(),
      });
      setLoading(false);
    }
  }

  function clearHistory() {
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY);
  }

  return (
    <div className="flex flex-col h-full">
      <header className="p-4 border-b border-border flex items-center gap-3">
        <h2 className="text-lg font-semibold">Chat</h2>
        <div className="flex-1" />
        <label className="flex items-center gap-1.5 text-xs text-muted">
          <input
            type="checkbox"
            checked={showTools}
            onChange={(e) => setShowTools(e.target.checked)}
            className="rounded"
          />
          Show tools
        </label>
        {messages.length > 0 && (
          <button
            onClick={clearHistory}
            className="text-xs text-muted hover:text-error"
          >
            Clear history
          </button>
        )}
      </header>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !loading && (
          <div className="flex items-center justify-center h-full text-muted">
            <p>Send a message to start chatting with your bot.</p>
          </div>
        )}
        {messages.map((msg, i) => (
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
              {showTools && msg.tools && msg.tools.length > 0 && (
                <details className="mt-2 pt-2 border-t border-border">
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
        {loading && (
          <div className="flex justify-start">
            <div className="max-w-[75%] rounded-xl px-4 py-2.5 text-sm bg-card border border-border">
              {streamText ? (
                <div className="whitespace-pre-wrap">{streamText}</div>
              ) : activeTools.length > 0 ? (
                <div className="text-muted">
                  <span>Using {activeTools[activeTools.length - 1]}...</span>
                  <ul className="mt-1 text-xs space-y-0.5">
                    {activeTools.map((t, j) => (
                      <li key={j}>• {t}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <span className="text-muted">Thinking...</span>
              )}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="p-4 border-t border-border">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            className="flex-1 bg-card border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-accent hover:bg-accent-hover text-white px-6 py-2.5 rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
