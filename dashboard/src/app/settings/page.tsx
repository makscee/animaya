"use client";

import { useState, useEffect } from "react";

export default function SettingsPage() {
  const [model, setModel] = useState("claude-sonnet-4-6");
  const [language, setLanguage] = useState("");
  const [showTools, setShowTools] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch("/api/settings")
      .then((r) => r.json())
      .then((data) => {
        setModel(data.model || "claude-sonnet-4-6");
        setLanguage(data.mainLanguage || "");
        setShowTools(data.showTools || false);
      })
      .catch(() => {});
  }, []);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    try {
      await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model, mainLanguage: language, showTools }),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      <header className="p-4 border-b border-border">
        <h2 className="text-lg font-semibold">Settings</h2>
      </header>

      <div className="flex-1 overflow-y-auto p-4 max-w-lg">
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium mb-1.5">Model</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="claude-sonnet-4-6">Claude Sonnet 4.6 (recommended)</option>
              <option value="claude-opus-4-6">Claude Opus 4.6</option>
              <option value="claude-haiku-4-5-20251001">Claude Haiku 4.5 (faster, cheaper)</option>
            </select>
            <p className="text-xs text-muted mt-1">
              The AI model your bot uses. Sonnet is the best balance of speed and quality.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">Main Language</label>
            <input
              type="text"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              placeholder="e.g., English, Russian, Spanish"
              className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            />
            <p className="text-xs text-muted mt-1">
              Your bot will prefer this language in responses.
            </p>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium">Verbose Tool Usage</label>
              <p className="text-xs text-muted">
                Show the list of tools used while the bot is thinking (kept visible, not deleted).
              </p>
            </div>
            <button
              onClick={() => setShowTools(!showTools)}
              className={`relative w-11 h-6 rounded-full transition-colors ${
                showTools ? "bg-accent" : "bg-border"
              }`}
            >
              <span
                className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
                  showTools ? "translate-x-5" : ""
                }`}
              />
            </button>
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            className="bg-accent hover:bg-accent-hover text-white px-6 py-2.5 rounded-lg text-sm font-medium disabled:opacity-50"
          >
            {saving ? "Saving..." : saved ? "✓ Saved" : "Save Settings"}
          </button>
        </div>
      </div>
    </div>
  );
}
