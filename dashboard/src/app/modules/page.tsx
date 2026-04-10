"use client";

import { useState, useEffect } from "react";
import { MODULE_DEFINITIONS } from "@/lib/modules";
import type { InstallStep } from "@/lib/types";

export default function ModulesPage() {
  const [installed, setInstalled] = useState<Record<string, boolean>>({});
  const [installing, setInstalling] = useState<string | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadModules();
  }, []);

  async function loadModules() {
    try {
      const res = await fetch("/api/modules");
      const data = await res.json();
      const map: Record<string, boolean> = {};
      for (const m of data.modules || []) {
        map[m.id] = m.installed;
      }
      setInstalled(map);
    } catch {
      // API not available yet — show all as uninstalled
    } finally {
      setLoading(false);
    }
  }

  function startInstall(moduleId: string) {
    setInstalling(moduleId);
    setStepIndex(0);
    setFormData({});
  }

  function cancelInstall() {
    setInstalling(null);
    setStepIndex(0);
    setFormData({});
  }

  async function finishInstall() {
    if (!installing) return;
    try {
      await fetch(`/api/modules/${installing}/install`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      setInstalled((prev) => ({ ...prev, [installing]: true }));
    } catch {
      // handle error
    }
    cancelInstall();
  }

  function nextStep() {
    const mod = MODULE_DEFINITIONS.find((m) => m.id === installing);
    if (!mod?.installSteps) return;
    if (stepIndex < mod.installSteps.length - 1) {
      setStepIndex((prev) => prev + 1);
    } else {
      finishInstall();
    }
  }

  async function handleUninstall(moduleId: string) {
    try {
      await fetch(`/api/modules/${moduleId}/uninstall`, { method: "POST" });
      setInstalled((prev) => ({ ...prev, [moduleId]: false }));
    } catch {
      // handle error
    }
  }

  const currentModule = installing ? MODULE_DEFINITIONS.find((m) => m.id === installing) : null;
  const currentStep: InstallStep | undefined = currentModule?.installSteps?.[stepIndex];

  const categories = ["core", "integration", "feature"] as const;
  const categoryLabels = { core: "Core", integration: "Integrations", feature: "Features" };

  return (
    <div className="flex flex-col h-full">
      <header className="p-4 border-b border-border">
        <h2 className="text-lg font-semibold">Modules</h2>
        <p className="text-sm text-muted">Install features to customize your assistant</p>
      </header>

      {/* Install wizard modal */}
      {installing && currentStep && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-xl w-full max-w-md mx-4 p-6">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xl">{currentModule?.icon}</span>
              <h3 className="font-semibold">{currentModule?.name}</h3>
            </div>
            <div className="text-xs text-muted mb-4">
              Step {stepIndex + 1} of {currentModule?.installSteps?.length}
            </div>

            <h4 className="font-medium mb-1">{currentStep.title}</h4>
            <p className="text-sm text-muted mb-4">{currentStep.description}</p>

            {currentStep.type === "input" && currentStep.field && (
              <input
                type="text"
                value={formData[currentStep.field] || ""}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, [currentStep.field!]: e.target.value }))
                }
                placeholder={currentStep.placeholder}
                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent mb-4"
              />
            )}

            <div className="flex gap-2 justify-end">
              <button
                onClick={cancelInstall}
                className="px-4 py-2 text-sm text-muted hover:text-foreground"
              >
                Cancel
              </button>
              <button
                onClick={nextStep}
                disabled={
                  currentStep.type === "input" &&
                  !!currentStep.field &&
                  !formData[currentStep.field]
                }
                className="bg-accent hover:bg-accent-hover text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
              >
                {stepIndex === (currentModule?.installSteps?.length ?? 1) - 1
                  ? "Install"
                  : "Next"}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="text-center text-muted py-8">Loading modules...</div>
        ) : (
          categories.map((cat) => {
            const mods = MODULE_DEFINITIONS.filter((m) => m.category === cat);
            if (mods.length === 0) return null;
            return (
              <div key={cat} className="mb-6">
                <h3 className="text-sm font-semibold text-muted uppercase tracking-wider mb-3">
                  {categoryLabels[cat]}
                </h3>
                <div className="grid gap-3 sm:grid-cols-2">
                  {mods.map((mod) => {
                    const isInstalled = installed[mod.id];
                    const missingDeps = (mod.requires || []).filter((r) => !installed[r]);
                    return (
                      <div
                        key={mod.id}
                        className="bg-card border border-border rounded-xl p-4 flex flex-col"
                      >
                        <div className="flex items-start gap-3 mb-2">
                          <span className="text-2xl">{mod.icon}</span>
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <h4 className="font-medium">{mod.name}</h4>
                              {isInstalled && (
                                <span className="text-xs bg-success/20 text-success px-2 py-0.5 rounded-full">
                                  Installed
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-muted mt-0.5">{mod.description}</p>
                          </div>
                        </div>
                        <div className="mt-auto pt-2">
                          {isInstalled ? (
                            <button
                              onClick={() => handleUninstall(mod.id)}
                              className="text-xs text-error hover:underline"
                            >
                              Uninstall
                            </button>
                          ) : missingDeps.length > 0 ? (
                            <span className="text-xs text-warning">
                              Requires: {missingDeps.join(", ")}
                            </span>
                          ) : (
                            <button
                              onClick={() => startInstall(mod.id)}
                              className="bg-accent hover:bg-accent-hover text-white px-4 py-1.5 rounded-lg text-xs font-medium"
                            >
                              Install
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
