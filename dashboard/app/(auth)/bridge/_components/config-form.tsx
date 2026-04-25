"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
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
import { Input } from "@/components/ui/input";
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
  type BridgePolicyPayloadType,
  type BridgeTogglePayloadType,
} from "@/lib/schemas";

type BridgeIdentity = {
  ok: boolean;
  username: string | null;
  error: string | null;
};

type BridgeStatus = {
  installed: boolean;
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
  const { data: identity, mutate: mutateIdentity } = useSWR<BridgeIdentity>(
    "/api/bridge/identity",
    fetcher,
  );
  const [claimCode, setClaimCode] = useState<string | null>(null);
  const [claimExpires, setClaimExpires] = useState<string | null>(null);
  const [tokenInput, setTokenInput] = useState("");
  const [tokenSaving, setTokenSaving] = useState(false);

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
    const body = (await res.json().catch(() => ({}))) as {
      code?: string;
      expires_at?: string;
    };
    if (body.code) setClaimCode(body.code);
    if (body.expires_at) setClaimExpires(body.expires_at);
    toast.success("Claim code issued");
    void mutate();
  };
  const revoke = async () => {
    const res = await postJson("/api/bridge/revoke");
    if (!res.ok) return toast.error("Revoke failed");
    setClaimCode(null);
    setClaimExpires(null);
    toast.success("Bridge revoked");
    void mutate();
  };
  const regen = async () => {
    const res = await postJson("/api/bridge/regen");
    if (!res.ok) return toast.error("Regenerate failed");
    const body = (await res.json().catch(() => ({}))) as {
      code?: string;
      expires_at?: string;
    };
    if (body.code) setClaimCode(body.code);
    if (body.expires_at) setClaimExpires(body.expires_at);
    toast.success("Claim code rotated");
    void mutate();
  };

  const saveToken = async () => {
    const token = tokenInput.trim();
    if (token.length < 20) {
      toast.error("Token looks too short");
      return;
    }
    setTokenSaving(true);
    try {
      const res = await putJson("/api/bridge/token", { token });
      const body = (await res.json().catch(() => ({}))) as BridgeIdentity & {
        error?: string;
      };
      if (!res.ok || !body.ok) {
        toast.error(`Token rejected: ${body.error ?? "unknown"}`);
        return;
      }
      toast.success(
        body.username
          ? `Token saved (@${body.username}). Reload bot for it to take effect.`
          : "Token saved. Reload bot for it to take effect.",
      );
      setTokenInput("");
      void mutateIdentity();
    } finally {
      setTokenSaving(false);
    }
  };

  if (isLoading || !data)
    return <div className="text-muted-foreground">Loading…</div>;

  if (!data.installed) {
    return (
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Telegram bridge not installed</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm text-muted-foreground">
          <p>
            Install the telegram-bridge module first to configure the claim,
            policy, and rotation controls.
          </p>
          <Link href="/modules" className="inline-flex">
            <Button data-testid="bridge-go-modules">Go to Modules</Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex max-w-2xl flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Status</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 text-sm">
          <div>
            Bot:{" "}
            {identity === undefined ? (
              <span className="text-muted-foreground">checking…</span>
            ) : identity.ok && identity.username ? (
              <a
                href={`https://t.me/${identity.username}`}
                target="_blank"
                rel="noreferrer"
                className="text-primary hover:underline"
              >
                @{identity.username}
              </a>
            ) : (
              <span className="text-destructive">
                {identity.error ?? "unknown"}
              </span>
            )}
          </div>
          <div>
            Owner:{" "}
            <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">
              {data.owner_id ?? "unclaimed"}
            </code>
          </div>
          <div>
            Claim code:{" "}
            {claimCode ? (
              <>
                <code
                  className="rounded bg-primary/20 px-2 py-0.5 font-mono text-sm text-primary"
                  data-testid="bridge-claim-code"
                >
                  {claimCode}
                </code>
                {claimExpires ? (
                  <span className="ml-2 text-xs text-muted-foreground">
                    expires {new Date(claimExpires).toLocaleTimeString()}
                  </span>
                ) : null}
                <p className="mt-1 text-xs text-muted-foreground">
                  Send this code to {identity?.username ? `@${identity.username}` : "the bot"} to link your Telegram account.
                </p>
              </>
            ) : data.claim_code_present ? (
              <span className="text-muted-foreground">
                present — press Regenerate to see it
              </span>
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
          <CardTitle>Bot token</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm">
          <p className="text-xs text-muted-foreground">
            Paste a fresh token from @BotFather. It will be validated via
            Telegram getMe before saving. The bot process must be restarted for
            the new token to take effect.
          </p>
          <div className="flex gap-2">
            <Input
              type="password"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="123456:ABCDEF…"
              className="font-mono"
              data-testid="bridge-token-input"
              autoComplete="off"
            />
            <Button
              onClick={saveToken}
              disabled={tokenSaving || tokenInput.trim().length < 20}
              data-testid="bridge-token-save"
            >
              {tokenSaving ? "Validating…" : "Save"}
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
