"use client";

import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useSSE, type SSEFrame } from "../_lib/use-sse";
import { ToolUseEvent, type ToolUseEventProps } from "./tool-use-event";

/**
 * Split-layout chat column (left side of /chat page).
 *
 * Maintains a rolling `turns` transcript. A turn is a single user message
 * plus the sequence of stream frames (text / tool_use / tool_result / end)
 * the engine produces in response. Input disables while a turn is streaming.
 */

type Turn = {
  id: string;
  user: string;
  frames: SSEFrame[];
};

const STORAGE_KEY = "animaya-chat-turns-v1";

export function ChatPanel() {
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [hydrated, setHydrated] = useState(false);
  const { events, status, send, reset } = useSSE("/api/chat/stream");
  const scrollRef = useRef<HTMLDivElement>(null);
  const turnIdRef = useRef<string | null>(null);

  // Hydrate from localStorage once on mount.
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) setTurns(parsed as Turn[]);
      }
    } catch {
      /* ignore corrupt state */
    }
    setHydrated(true);
  }, []);

  // Persist turns after hydration. Skipped pre-hydration to avoid
  // overwriting saved state with the initial empty array.
  useEffect(() => {
    if (!hydrated) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(turns));
    } catch {
      /* storage may be full or disabled */
    }
  }, [turns, hydrated]);

  // Attach newly-arrived frames to the currently-streaming turn.
  useEffect(() => {
    if (!turnIdRef.current || events.length === 0) return;
    setTurns((prev) =>
      prev.map((t) =>
        t.id === turnIdRef.current ? { ...t, frames: events } : t,
      ),
    );
  }, [events]);

  // Auto-scroll to bottom on new frames.
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [turns]);

  const clearHistory = () => {
    setTurns([]);
    turnIdRef.current = null;
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  };

  const submit = async () => {
    const message = draft.trim();
    if (!message || status === "streaming") return;
    const id = `t-${Date.now()}`;
    turnIdRef.current = id;
    setTurns((prev) => [...prev, { id, user: message, frames: [] }]);
    setDraft("");
    reset();
    await send({ message });
  };

  return (
    <div className="flex h-full min-w-0 flex-1 flex-col">
      {turns.length > 0 ? (
        <div className="flex justify-end border-b border-border px-4 py-2">
          <button
            type="button"
            onClick={clearHistory}
            className="text-xs text-muted-foreground hover:text-foreground"
            data-testid="chat-clear"
          >
            Clear history
          </button>
        </div>
      ) : null}
      <div
        ref={scrollRef}
        data-testid="chat-scroll"
        className="min-w-0 flex-1 overflow-y-auto p-4"
      >
        {turns.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            Start a conversation.
          </div>
        ) : (
          <div className="flex min-w-0 flex-col gap-4">
            {turns.map((turn) => (
              <div key={turn.id} className="flex min-w-0 flex-col gap-3">
                <div className="max-w-[80%] self-end break-words rounded-xl bg-primary px-3 py-2 text-sm text-primary-foreground">
                  {turn.user}
                </div>
                <div className="flex min-w-0 flex-col gap-2">
                  {turn.frames.map((f, i) => (
                    <ToolUseEvent
                      key={`${turn.id}-${i}`}
                      {...(f as ToolUseEventProps)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      <form
        className="flex gap-2 border-t border-border p-3"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <Textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Message Animaya…"
          rows={2}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void submit();
            }
          }}
          data-testid="chat-input"
        />
        <Button
          type="submit"
          disabled={status === "streaming" || draft.trim().length === 0}
          data-testid="chat-send"
        >
          <Send className="size-4" />
        </Button>
      </form>
    </div>
  );
}
