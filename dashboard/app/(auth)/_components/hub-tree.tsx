"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";
import { ChevronDown, ChevronRight, File, Folder } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Hub filesystem tree (DASH-03).
 *
 * - Collapsible directory nodes; open state persisted in
 *   localStorage["animaya.treeOpen"] as a string[] of absolute rel paths.
 * - Dotfile visibility toggled; preference persisted in
 *   localStorage["animaya.treeShowHidden"] (default false).
 * - Clicking a file triggers `onSelect(relpath)` — the parent page handles
 *   loading `/api/hub/file?path=` into the right-hand viewer pane.
 */

type TreeNode = {
  name: string;
  path: string;
  type: "file" | "dir";
  children?: TreeNode[];
};

type TreeResponse = { root: TreeNode };

const fetcher = (url: string) => fetch(url).then((r) => r.json());

const LS_OPEN = "animaya.treeOpen";
const LS_HIDDEN = "animaya.treeShowHidden";

function loadSet(key: string): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return new Set();
    const arr = JSON.parse(raw) as unknown;
    return Array.isArray(arr) ? new Set(arr.map(String)) : new Set();
  } catch {
    return new Set();
  }
}

function isDotfile(name: string): boolean {
  return name.startsWith(".");
}

export function HubTree({
  onSelect,
}: {
  onSelect?: (path: string) => void;
}) {
  const [showHidden, setShowHidden] = useState(false);
  const [open, setOpen] = useState<Set<string>>(new Set());

  useEffect(() => {
    setShowHidden(
      window.localStorage.getItem(LS_HIDDEN) === "true",
    );
    setOpen(loadSet(LS_OPEN));
  }, []);

  const persistOpen = (next: Set<string>) => {
    setOpen(new Set(next));
    window.localStorage.setItem(LS_OPEN, JSON.stringify(Array.from(next)));
  };

  const toggleHidden = () => {
    const next = !showHidden;
    setShowHidden(next);
    window.localStorage.setItem(LS_HIDDEN, String(next));
  };

  const { data, error, isLoading } = useSWR<TreeResponse>(
    `/api/hub/tree?path=&show_hidden=${showHidden}`,
    fetcher,
  );

  return (
    <aside
      className="flex h-full w-80 shrink-0 flex-col border-l border-border bg-sidebar"
      data-testid="hub-tree"
    >
      <div className="flex items-center justify-between border-b border-border p-2">
        <span className="text-xs font-semibold uppercase text-muted-foreground">
          Hub
        </span>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={toggleHidden}
          data-testid="hub-tree-toggle-hidden"
        >
          {showHidden ? "Hide dotfiles" : "Show hidden"}
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 text-sm">
        {isLoading ? (
          <div className="text-muted-foreground">Loading…</div>
        ) : error ? (
          <div className="text-destructive">Failed to load tree</div>
        ) : data?.root ? (
          <TreeRow
            node={data.root}
            open={open}
            setOpen={persistOpen}
            showHidden={showHidden}
            onSelect={onSelect}
            depth={0}
          />
        ) : (
          <div className="text-muted-foreground">Empty</div>
        )}
      </div>
    </aside>
  );
}

function TreeRow({
  node,
  open,
  setOpen,
  showHidden,
  onSelect,
  depth,
}: {
  node: TreeNode;
  open: Set<string>;
  setOpen: (s: Set<string>) => void;
  showHidden: boolean;
  onSelect?: (p: string) => void;
  depth: number;
}) {
  if (!showHidden && isDotfile(node.name) && depth > 0) return null;

  if (node.type === "file") {
    return (
      <button
        type="button"
        onClick={() => onSelect?.(node.path)}
        className="flex w-full items-center gap-1 rounded px-1 py-0.5 text-left hover:bg-accent"
        style={{ paddingLeft: 4 + depth * 12 }}
        data-testid="hub-tree-file"
      >
        <File className="size-3 shrink-0 text-muted-foreground" />
        <span className="truncate">{node.name}</span>
      </button>
    );
  }

  const isOpen = depth === 0 || open.has(node.path);
  const toggle = () => {
    const next = new Set(open);
    if (next.has(node.path)) next.delete(node.path);
    else next.add(node.path);
    setOpen(next);
  };
  return (
    <div>
      <button
        type="button"
        onClick={toggle}
        className="flex w-full items-center gap-1 rounded px-1 py-0.5 text-left hover:bg-accent"
        style={{ paddingLeft: 4 + depth * 12 }}
        data-testid="hub-tree-dir"
      >
        {isOpen ? (
          <ChevronDown className="size-3 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="size-3 shrink-0 text-muted-foreground" />
        )}
        <Folder className="size-3 shrink-0 text-primary" />
        <span className="truncate font-medium">
          {depth === 0 ? "/" : node.name}
        </span>
      </button>
      {isOpen
        ? (node.children ?? []).map((child) => (
            <TreeRow
              key={child.path}
              node={child}
              open={open}
              setOpen={setOpen}
              showHidden={showHidden}
              onSelect={onSelect}
              depth={depth + 1}
            />
          ))
        : null}
    </div>
  );
}
