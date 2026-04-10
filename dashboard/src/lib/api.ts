import type { Settings, LogEntry, Stats } from "./types";

const API_BASE = "/api";

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

// Modules
export const getModules = () => fetchJSON<{ modules: Array<{ id: string; installed: boolean; config?: Record<string, string> }> }>("/modules");
export const installModule = (id: string, config?: Record<string, string>) =>
  fetchJSON<{ ok: boolean }>(`/modules/${id}/install`, { method: "POST", body: JSON.stringify(config ?? {}) });
export const uninstallModule = (id: string) =>
  fetchJSON<{ ok: boolean }>(`/modules/${id}/uninstall`, { method: "POST" });

// Chat
export const sendMessage = (text: string) =>
  fetchJSON<{ messageId: string }>("/chat", { method: "POST", body: JSON.stringify({ text }) });

export function streamChat(onToken: (text: string) => void, onDone: (full: string) => void, onTool: (name: string) => void, onError: (err: string) => void) {
  const es = new EventSource(`${API_BASE}/chat/stream`);
  es.addEventListener("token", (e) => onToken(JSON.parse(e.data).text));
  es.addEventListener("done", (e) => { onDone(JSON.parse(e.data).fullText); es.close(); });
  es.addEventListener("tool", (e) => onTool(JSON.parse(e.data).name));
  es.addEventListener("error", (e) => { onError("Connection lost"); es.close(); });
  return es;
}

// Files
export const listFiles = (path: string = "") => fetchJSON<{ path: string; entries: Array<{ name: string; type: string; size: number | null }> }>(`/files?path=${encodeURIComponent(path)}`);
export const readFile = (path: string) => fetchJSON<{ path: string; content: string }>(`/files/read?path=${encodeURIComponent(path)}`);
export const writeFile = (path: string, content: string) =>
  fetchJSON<{ ok: boolean }>("/files", { method: "PUT", body: JSON.stringify({ path, content }) });
export const deleteFile = (path: string) =>
  fetchJSON<{ ok: boolean }>(`/files?path=${encodeURIComponent(path)}`, { method: "DELETE" });

// Settings
export const getSettings = () => fetchJSON<Settings>("/settings");
export const saveSettings = (settings: Partial<Settings>) =>
  fetchJSON<{ ok: boolean }>("/settings", { method: "PUT", body: JSON.stringify(settings) });

// Stats
export const getStats = () => fetchJSON<Stats>("/stats");

// Logs
export const getLogs = (level?: string, limit?: number) =>
  fetchJSON<{ entries: LogEntry[] }>(`/logs?level=${level ?? ""}&limit=${limit ?? 200}`);

// History
export const getHistory = (sessionId?: string) =>
  fetchJSON<{ sessions: Array<{ id: string; lastMessage: string; timestamp: string }> }>(`/chat/history${sessionId ? `?session=${sessionId}` : ""}`);
