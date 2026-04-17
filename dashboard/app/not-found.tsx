import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-[60vh] items-center justify-center p-8">
      <div className="text-center">
        <h1 className="text-2xl font-semibold">404 — Not Found</h1>
        <p className="mt-2 text-sm text-muted-foreground">The page you&apos;re looking for doesn&apos;t exist.</p>
        <Link href="/" className="mt-4 inline-block text-sm underline">Back to Overview</Link>
      </div>
    </main>
  );
}
