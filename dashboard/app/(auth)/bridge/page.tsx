import { BridgeConfigForm } from "./_components/config-form";

export const dynamic = "force-dynamic";

export default function BridgePage() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold">Bridge</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Telegram bridge claim, policy, and rotation.
        </p>
      </div>
      <BridgeConfigForm />
    </div>
  );
}
