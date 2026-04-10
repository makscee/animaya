"use client";

import { useState, useEffect } from "react";

interface FileEntry {
  name: string;
  type: string;
  size: number | null;
}

export default function FilesPage() {
  const [path, setPath] = useState("");
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [editingPath, setEditingPath] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadDir(path);
  }, [path]);

  async function loadDir(dirPath: string) {
    setFileContent(null);
    setEditingPath(null);
    try {
      const res = await fetch(`/api/files?path=${encodeURIComponent(dirPath)}`);
      const data = await res.json();
      if (data.content !== undefined) {
        setFileContent(data.content);
        setEditingPath(dirPath);
        setEditContent(data.content);
      } else {
        setEntries(data.entries || []);
      }
    } catch {
      setEntries([]);
    }
  }

  function navigate(name: string, type: string) {
    const newPath = path ? `${path}/${name}` : name;
    if (type === "dir") {
      setPath(newPath);
    } else {
      setPath(newPath);
    }
  }

  function goUp() {
    const parts = path.split("/").filter(Boolean);
    parts.pop();
    setPath(parts.join("/"));
  }

  async function saveFile() {
    if (!editingPath) return;
    setSaving(true);
    try {
      await fetch("/api/files", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: editingPath, content: editContent }),
      });
    } finally {
      setSaving(false);
    }
  }

  function formatSize(bytes: number | null): string {
    if (bytes === null) return "";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  return (
    <div className="flex flex-col h-full">
      <header className="p-4 border-b border-border flex items-center gap-3">
        <h2 className="text-lg font-semibold">Files</h2>
        <span className="text-sm text-muted font-mono">/{path}</span>
      </header>

      {fileContent !== null ? (
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex items-center gap-2 p-3 border-b border-border bg-sidebar">
            <button onClick={goUp} className="text-sm text-accent hover:underline">
              ← Back
            </button>
            <span className="text-sm font-mono text-muted">{editingPath}</span>
            <div className="flex-1" />
            <button
              onClick={saveFile}
              disabled={saving}
              className="bg-accent hover:bg-accent-hover text-white px-4 py-1.5 rounded text-sm disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
          <textarea
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            className="flex-1 bg-background font-mono text-sm p-4 resize-none focus:outline-none"
            spellCheck={false}
          />
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          {path && (
            <button
              onClick={goUp}
              className="w-full text-left px-4 py-2.5 border-b border-border text-sm hover:bg-card-hover flex items-center gap-2"
            >
              <span>📁</span>
              <span className="text-muted">..</span>
            </button>
          )}
          {entries.map((entry) => (
            <button
              key={entry.name}
              onClick={() => navigate(entry.name, entry.type)}
              className="w-full text-left px-4 py-2.5 border-b border-border text-sm hover:bg-card-hover flex items-center gap-2"
            >
              <span>{entry.type === "dir" ? "📁" : "📄"}</span>
              <span className="flex-1">{entry.name}</span>
              <span className="text-xs text-muted">{formatSize(entry.size)}</span>
            </button>
          ))}
          {entries.length === 0 && (
            <div className="p-8 text-center text-muted">Empty directory</div>
          )}
        </div>
      )}
    </div>
  );
}
