"use client";

import { useState } from "react";
import { ChatPanel } from "../_components/chat-panel";
import { HubTree } from "../_components/hub-tree";

/**
 * Client composite: chat (flex-1) | hub-tree (w-80) split. Selecting a file
 * in the tree opens a read-only viewer overlay above the tree column.
 */
export function ChatWithTree() {
  const [viewing, setViewing] = useState<{ path: string; content: string } | null>(
    null,
  );

  const openFile = async (path: string) => {
    const res = await fetch(`/api/hub/file?path=${encodeURIComponent(path)}`);
    if (!res.ok) return;
    const data = (await res.json()) as { content?: string };
    setViewing({ path, content: data.content ?? "" });
  };

  return (
    <>
      <ChatPanel />
      <div className="relative flex">
        <HubTree onSelect={openFile} />
        {viewing ? (
          <div
            data-testid="hub-viewer"
            className="absolute right-0 top-0 flex h-full w-[40rem] flex-col border-l border-border bg-background shadow-xl"
          >
            <div className="flex items-center justify-between border-b border-border p-2 text-xs">
              <span className="truncate font-mono">{viewing.path}</span>
              <button
                type="button"
                className="text-muted-foreground hover:text-foreground"
                onClick={() => setViewing(null)}
              >
                close
              </button>
            </div>
            <pre className="flex-1 overflow-auto p-3 text-xs">
              {viewing.content}
            </pre>
          </div>
        ) : null}
      </div>
    </>
  );
}
