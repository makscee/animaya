"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * SSE-over-POST hook.
 *
 * Our engine exposes `/api/chat/stream` as an SSE endpoint that REQUIRES a
 * POST body (message + optional session_id) — `EventSource` only speaks GET,
 * so we do the stream read manually via fetch's `response.body.getReader()`.
 *
 * Attaches the `an-csrf` double-submit cookie value as `x-csrf-token` per
 * the CSRF scheme established in Plan 13-02 (lib/csrf.server.ts).
 *
 * Reconnect: on normal stream close we do NOT auto-reconnect (we treat a
 * clean `data: {"type":"end"}` as turn-complete). On abnormal close
 * (network / server error) we reconnect with exponential backoff capped at
 * 30 s. Callers drive new turns by calling `send()` again.
 */

export type SSEFrame = Record<string, unknown>;

export type SSEStatus = "idle" | "streaming" | "error" | "closed";

function readCsrfCookie(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|;\s*)an-csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

export function useSSE(url: string) {
  const [events, setEvents] = useState<SSEFrame[]>([]);
  const [status, setStatus] = useState<SSEStatus>("idle");
  const abortRef = useRef<AbortController | null>(null);
  const retryRef = useRef<number>(0);

  const reset = useCallback(() => {
    setEvents([]);
  }, []);

  const send = useCallback(
    async (payload: unknown): Promise<void> => {
      // Cancel any in-flight stream before starting a new turn.
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      setStatus("streaming");

      const attempt = async (): Promise<void> => {
        let res: Response;
        try {
          res = await fetch(url, {
            method: "POST",
            signal: ctrl.signal,
            headers: {
              "content-type": "application/json",
              "x-csrf-token": readCsrfCookie(),
              accept: "text/event-stream",
            },
            body: JSON.stringify(payload),
          });
        } catch (err) {
          if ((err as { name?: string }).name === "AbortError") return;
          throw err;
        }
        if (!res.ok || !res.body) {
          throw new Error(`SSE HTTP ${res.status}`);
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buf += decoder.decode(value, { stream: true });
            // SSE frames are delimited by a blank line (\n\n).
            let idx: number;
            while ((idx = buf.indexOf("\n\n")) !== -1) {
              const rawFrame = buf.slice(0, idx);
              buf = buf.slice(idx + 2);
              for (const line of rawFrame.split("\n")) {
                if (!line.startsWith("data:")) continue; // skip `:ping`
                const data = line.slice(5).trimStart();
                if (!data) continue;
                try {
                  const parsed = JSON.parse(data) as SSEFrame;
                  setEvents((prev) => [...prev, parsed]);
                  if ((parsed as { type?: string }).type === "end") {
                    setStatus("closed");
                    return;
                  }
                } catch {
                  // Malformed JSON — surface as raw text frame.
                  setEvents((prev) => [...prev, { type: "raw", data }]);
                }
              }
            }
          }
          setStatus("closed");
        } finally {
          reader.releaseLock();
        }
      };

      try {
        await attempt();
        retryRef.current = 0;
      } catch (err) {
        if ((err as { name?: string }).name === "AbortError") {
          setStatus("closed");
          return;
        }
        // Exponential backoff, capped at 30s, single retry per turn.
        const delay = Math.min(30_000, 1000 * 2 ** retryRef.current);
        retryRef.current += 1;
        setStatus("error");
        await new Promise((r) => setTimeout(r, delay));
        if (ctrl.signal.aborted) return;
        try {
          await attempt();
          retryRef.current = 0;
        } catch {
          setStatus("error");
        }
      }
    },
    [url],
  );

  useEffect(() => () => abortRef.current?.abort(), []);

  return { events, status, send, reset };
}
