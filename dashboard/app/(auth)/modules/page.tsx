import { ModulesList } from "./modules-list";

export const dynamic = "force-dynamic";

export default function ModulesPage() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold">Modules</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Installable capabilities. Each module advertises its own config shape.
        </p>
      </div>
      <ModulesList />
    </div>
  );
}
