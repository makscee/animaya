"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="flex min-h-[60vh] items-center justify-center p-8">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-destructive">Something went wrong</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {process.env.NODE_ENV !== "production"
            ? error.message
            : "An unexpected error occurred. Use the digest below to report this."}
        </p>
        {error.digest ? (
          <p className="mt-1 font-mono text-xs text-muted-foreground">digest: {error.digest}</p>
        ) : null}
        <button
          onClick={() => reset()}
          className="mt-4 rounded-md bg-primary px-4 py-1.5 text-sm text-primary-foreground"
        >
          Retry
        </button>
      </div>
    </main>
  );
}
