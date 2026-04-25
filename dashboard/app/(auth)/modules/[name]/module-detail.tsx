"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import useSWR from "swr";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { BridgeConfigForm } from "../../bridge/_components/config-form";

type SchemaProperty = {
  type?: string;
  default?: unknown;
  description?: string;
  minimum?: number;
  maximum?: number;
  enum?: unknown[];
};

type ConfigSchema = {
  type?: string;
  properties?: Record<string, SchemaProperty>;
  required?: string[];
};

type ModuleDetailResponse = {
  name: string;
  installed: boolean;
  has_config?: boolean;
  description?: string;
  readme?: string;
  version?: string;
  config_schema?: ConfigSchema | null;
  config: Record<string, unknown>;
};

const fetcher = (url: string) =>
  fetch(url).then(async (r) => {
    if (!r.ok) {
      const body = await r.json().catch(() => ({}));
      throw Object.assign(new Error(`HTTP ${r.status}`), {
        status: r.status,
        body,
      });
    }
    return r.json();
  });

function readCsrf(): string {
  if (typeof document === "undefined") return "";
  const m = document.cookie.match(/(?:^|;\s*)an-csrf=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}

async function installModule(name: string) {
  return fetch(`/api/modules/${name}/install`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-csrf-token": readCsrf(),
    },
    body: JSON.stringify({}),
  });
}

// Strip a leading markdown heading marker (e.g. "## Git Versioning Module"
// → "Git Versioning Module") for use as a plain subtitle.
function cleanDescription(raw?: string): string {
  if (!raw) return "";
  const first = raw.split("\n")[0].trim();
  return first.replace(/^#+\s*/, "");
}

function SchemaField({
  name,
  prop,
  required,
  value,
  onChange,
}: {
  name: string;
  prop: SchemaProperty;
  required: boolean;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const defText =
    prop.default !== undefined ? `default: ${JSON.stringify(prop.default)}` : "";
  const hint = [prop.description, defText].filter(Boolean).join(" · ");
  const label = (
    <div className="flex items-baseline justify-between">
      <span className="font-mono text-xs">
        {name}
        {required ? <span className="text-destructive">*</span> : null}
      </span>
      {prop.type ? (
        <span className="text-[0.65rem] uppercase tracking-wide text-muted-foreground">
          {prop.type}
        </span>
      ) : null}
    </div>
  );

  let control: React.ReactNode;
  if (prop.enum && prop.enum.length > 0) {
    const current = value === undefined ? String(prop.default ?? "") : String(value);
    control = (
      <Select value={current} onValueChange={(v) => onChange(v)}>
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {prop.enum.map((opt) => (
            <SelectItem key={String(opt)} value={String(opt)}>
              {String(opt)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  } else if (prop.type === "boolean") {
    const checked = value === undefined ? Boolean(prop.default) : Boolean(value);
    control = (
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="size-4 accent-primary"
        />
        <span className="text-muted-foreground">{checked ? "enabled" : "disabled"}</span>
      </label>
    );
  } else if (prop.type === "integer" || prop.type === "number") {
    const current =
      value === undefined
        ? prop.default !== undefined
          ? String(prop.default)
          : ""
        : String(value);
    control = (
      <Input
        type="number"
        value={current}
        min={prop.minimum}
        max={prop.maximum}
        step={prop.type === "integer" ? 1 : "any"}
        placeholder={
          prop.default !== undefined ? String(prop.default) : undefined
        }
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") return onChange(undefined);
          const n = prop.type === "integer" ? parseInt(raw, 10) : parseFloat(raw);
          onChange(Number.isFinite(n) ? n : undefined);
        }}
      />
    );
  } else {
    const current =
      value === undefined
        ? prop.default !== undefined
          ? String(prop.default)
          : ""
        : String(value);
    control = (
      <Input
        type="text"
        value={current}
        placeholder={
          prop.default !== undefined ? String(prop.default) : undefined
        }
        onChange={(e) => onChange(e.target.value === "" ? undefined : e.target.value)}
      />
    );
  }

  return (
    <div className="flex flex-col gap-1.5">
      {label}
      {control}
      {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

export function ModuleDetail({ name }: { name: string }) {
  const { data, mutate, isLoading, error } = useSWR<ModuleDetailResponse>(
    `/api/modules/${name}`,
    fetcher,
  );

  const [values, setValues] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (data?.config) setValues(data.config);
  }, [data]);

  const save = async () => {
    setSaving(true);
    try {
      const res = await fetch(`/api/modules/${name}/config`, {
        method: "PUT",
        headers: {
          "content-type": "application/json",
          "x-csrf-token": readCsrf(),
        },
        body: JSON.stringify(values),
      });
      if (!res.ok) {
        toast.error("Failed to save config");
        return;
      }
      toast.success("Config saved");
      void mutate();
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) return <div className="text-muted-foreground">Loading…</div>;
  if (error || !data)
    return <div className="text-destructive">Failed to load module</div>;

  // Telegram bridge has its own rich config UI — reuse it.
  if (data.installed && name === "telegram-bridge") {
    return <BridgeConfigForm />;
  }

  const blurb = cleanDescription(data.description);

  if (!data.installed) {
    return (
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Not installed</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm">
          {blurb ? <p className="text-muted-foreground">{blurb}</p> : null}
          <Button
            data-testid="module-detail-install"
            onClick={async () => {
              const res = await installModule(name);
              if (!res.ok) {
                toast.error(`Failed to install ${name}`);
                return;
              }
              toast.success(`Installed ${name}`);
              void mutate();
            }}
          >
            Install
          </Button>
        </CardContent>
      </Card>
    );
  }

  const schemaProps = data.config_schema?.properties ?? {};
  const entries = Object.entries(schemaProps);
  const required = new Set(data.config_schema?.required ?? []);

  return (
    <div className="flex max-w-2xl flex-col gap-4">
      {blurb ? (
        <p className="text-sm text-muted-foreground">{blurb}</p>
      ) : null}

      {entries.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Configuration</CardTitle>
          </CardHeader>
          <CardContent>
            <form
              data-testid="module-config-form"
              onSubmit={(e) => {
                e.preventDefault();
                void save();
              }}
              className="flex flex-col gap-4"
            >
              {entries.map(([key, prop]) => (
                <SchemaField
                  key={key}
                  name={key}
                  prop={prop}
                  required={required.has(key)}
                  value={values[key]}
                  onChange={(v) =>
                    setValues((prev) => {
                      const next = { ...prev };
                      if (v === undefined) delete next[key];
                      else next[key] = v;
                      return next;
                    })
                  }
                />
              ))}
              <Button type="submit" disabled={saving} className="self-start">
                {saving ? "Saving…" : "Save"}
              </Button>
            </form>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-4 text-sm text-muted-foreground">
            This module has no configurable fields.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
