import { ModuleDetail } from "./module-detail";

export const dynamic = "force-dynamic";

export default async function ModuleDetailPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;
  return (
    <div>
      <div className="mb-6">
        <h1 className="font-mono text-xl font-semibold">{name}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Module configuration.
        </p>
      </div>
      <ModuleDetail name={name} />
    </div>
  );
}
