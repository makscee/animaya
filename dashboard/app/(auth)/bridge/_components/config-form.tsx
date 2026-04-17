"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import useSWR from "swr";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  BridgePolicyPayload,
  BridgeTogglePayload,
  type BridgePolicyPayload as BridgePolicyPayloadType,
  type BridgeTogglePayload as BridgeTogglePayloadType,
} from "@/lib/schemas";

type BridgeStatus = {
  enabled: boolean;
  policy: "owner_only" | "allowlist" | "open";
  owner_id: string | null;
  claim_code_present: boolean;
};

const fetcher = (url: string) => fetch(url).then((r) => r.json());

function readCsrf(): string {
  if (typeof document === "undefined") return "";
  const m = document.cookie.match(/(?:^|;\s*)an-csrf=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}

async function postJson(url: string, body?: unknown) {
  return fetch(url, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-csrf-token": readCsrf(),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
}

async function putJson(url: string, body: unknown) {
  return fetch(url, {
    method: "PUT",
    headers: {
      "content-type": "application/json",
      "x-csrf-token": readCsrf(),
    },
    body: JSON.stringify(body),
  });
}

export function BridgeConfigForm() {
  const { data, mutate, isLoading } = useSWR<BridgeStatus>(
    "/api/bridge",
    fetcher,
  );

  // Toggle form (D-15: rhf + zodResolver)
  const toggleForm = useForm<BridgeTogglePayloadType>({
    resolver: zodResolver(BridgeTogglePayload),
    defaultValues: { enabled: false },
  });

  // Policy form
  const policyForm = useForm<BridgePolicyPayloadType>({
    resolver: zodResolver(BridgePolicyPayload),
    defaultValues: { policy: "owner_only" },
  });

  useEffect(() => {
    if (!data) return;
    toggleForm.reset({ enabled: data.enabled });
    policyForm.reset({ policy: data.policy });
  }, [data, toggleForm, policyForm]);

  const onToggle = toggleForm.handleSubmit(async (vals) => {
    const res = await putJson("/api/bridge/toggle", vals);
    if (!res.ok) return toast.error("Toggle failed");
    toast.success(vals.enabled ? "Bridge enabled" : "Bridge disabled");
    void mutate();
  });

  const onPolicy = policyForm.handleSubmit(async (vals) => {
    const res = await putJson("/api/bridge/policy", vals);
    if (!res.ok) return toast.error("Policy update failed");
    toast.success(`Policy: ${vals.policy}`);
    void mutate();
  });

  const claim = async () => {
    const res = await postJson("/api/bridge/claim");
    if (!res.ok) return toast.error("Claim failed");
    toast.success("Claim code issued");
    void mutate();
  };
  const revoke = async () => {
    const res = await postJson("/api/bridge/revoke");
    if (!res.ok) return toast.error("Revoke failed");
    toast.success("Bridge revoked");
    void mutate();
  };
  const regen = async () => {
    const res = await postJson("/api/bridge/regenerate");
    if (!res.ok) return toast.error("Regenerate failed");
    toast.success("Claim code rotated");
    void mutate();
  };

  if (isLoading || !data)
    return <div className="text-muted-foreground">Loading…</div>;

  return (
    <div className="flex max-w-2xl flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Status</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 text-sm">
          <div>
            Owner:{" "}
            <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">
              {data.owner_id ?? "unclaimed"}
            </code>
          </div>
          <div>
            Claim code:{" "}
            {data.claim_code_present ? (
              <span className="text-primary">present (redacted)</span>
            ) : (
              <span className="text-muted-foreground">none</span>
            )}
          </div>
          <div className="mt-2 flex gap-2">
            <Button onClick={claim} data-testid="bridge-claim">
              Claim
            </Button>
            <Button onClick={regen} variant="outline" data-testid="bridge-regen">
              Regenerate
            </Button>
            <Button
              onClick={revoke}
              variant="destructive"
              data-testid="bridge-revoke"
            >
              Revoke
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Enabled</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onToggle} className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                {...toggleForm.register("enabled")}
                data-testid="bridge-toggle-checkbox"
              />
              Bridge accepting messages
            </label>
            <Button type="submit" data-testid="bridge-toggle-save">
              Save
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Policy</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onPolicy} className="flex items-center gap-3">
            <Select
              value={policyForm.watch("policy")}
              onValueChange={(v) =>
                policyForm.setValue(
                  "policy",
                  v as BridgePolicyPayloadType["policy"],
                  { shouldValidate: true },
                )
              }
            >
              <SelectTrigger
                className="w-56"
                data-testid="bridge-policy-select"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="owner_only">owner_only</SelectItem>
                <SelectItem value="allowlist">allowlist</SelectItem>
                <SelectItem value="open">open</SelectItem>
              </SelectContent>
            </Select>
            <Button type="submit" data-testid="bridge-policy-save">
              Save
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
