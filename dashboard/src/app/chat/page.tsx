"use client";

import { useState, useRef, useEffect } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  tools?: string[];
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [activeTools, setActiveTools] = useState<string[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamText]);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    setStreamText("");
    setActiveTools([]);

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
        setActiveTools((prev) => [...prev, data.name]);
      });
      es.addEventListener("done", (e) => {
        const data = JSON.parse(e.data);
        es.close();
        setStreamText("");
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.fullText, tools: activeTools },
        ]);
        setLoading(false);
        setActiveTools([]);
      });
      es.addEventListener("error", () => {
        es.close();
        setStreamText("");
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Connection lost. Please try again." },
        ]);
        setLoading(false);
      });
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Failed to send message. Is the bot running?" },
      ]);
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      <header className="p-4 border-b border-border">
        <h2 className="text-lg font-semibold">Chat</h2>
      </header>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !loading && (
          <div className="flex items-center justify-center h-full text-muted">
            <p>Send a message to start chatting with your bot.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[75%] rounded-xl px-4 py-2.5 text-sm ${
                msg.role === "user"
                  ? "bg-accent text-white"
                  : "bg-card border border-border"
              }`}
            >
              <div className="whitespace-pre-wrap">{msg.content}</div>
              {msg.tools && msg.tools.length > 0 && (
                <div className="mt-2 pt-2 border-t border-border text-xs text-muted">
                  Tools: {msg.tools.join(", ")}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="max-w-[75%] rounded-xl px-4 py-2.5 text-sm bg-card border border-border">
              {streamText ? (
                <div className="whitespace-pre-wrap">{streamText}</div>
              ) : (
                <div className="flex items-center gap-2 text-muted">
                  {activeTools.length > 0 ? (
                    <span>Using {activeTools[activeTools.length - 1]}...</span>
                  ) : (
                    <span>Thinking...</span>
                  )}
                </div>
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
