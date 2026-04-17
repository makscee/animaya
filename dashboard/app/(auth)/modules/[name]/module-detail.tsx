"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import useSWR from "swr";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  ModuleConfigFormSchema,
  type ModuleConfigPayload,
} from "@/lib/schemas";

type ModuleDetailResponse = {
  name: string;
  installed: boolean;
  config: Record<string, unknown>;
};

const fetcher = (url: string) => fetch(url).then((r) => r.json());

function readCsrf(): string {
  if (typeof document === "undefined") return "";
  const m = document.cookie.match(/(?:^|;\s*)an-csrf=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}

export function ModuleDetail({ name }: { name: string }) {
  const { data, mutate, isLoading } = useSWR<ModuleDetailResponse>(
    `/api/modules/${name}`,
    fetcher,
  );

  const form = useForm<ModuleConfigPayload>({
    resolver: zodResolver(ModuleConfigFormSchema),
    defaultValues: { config: {} },
  });

  useEffect(() => {
    if (data?.config) form.reset({ config: data.config });
  }, [data, form]);

  const onSubmit = form.handleSubmit(async (values) => {
    const res = await fetch(`/api/modules/${name}/config`, {
      method: "PUT",
      headers: {
        "content-type": "application/json",
        "x-csrf-token": readCsrf(),
      },
      body: JSON.stringify(values.config),
    });
    if (!res.ok) {
      toast.error("Failed to save config");
      return;
    }
    toast.success("Config saved");
    void mutate();
  });

  if (isLoading || !data)
    return <div className="text-muted-foreground">Loading…</div>;

  return (
    <form
      onSubmit={onSubmit}
      className="flex max-w-2xl flex-col gap-4"
      data-testid="module-config-form"
    >
      <label className="flex flex-col gap-2">
        <span className="text-sm font-medium">Config (JSON)</span>
        <Textarea
          rows={12}
          defaultValue={JSON.stringify(data.config, null, 2)}
          onChange={(e) => {
            try {
              form.setValue(
                "config",
                JSON.parse(e.target.value) as Record<string, unknown>,
              );
              form.clearErrors("config");
            } catch {
              form.setError("config", { message: "Invalid JSON" });
            }
          }}
        />
        {form.formState.errors.config ? (
          <span className="text-xs text-destructive">
            {String(form.formState.errors.config.message ?? "Invalid")}
          </span>
        ) : null}
      </label>
      <Button type="submit" disabled={!form.formState.isValid && form.formState.isSubmitted}>
        Save
      </Button>
    </form>
  );
}
