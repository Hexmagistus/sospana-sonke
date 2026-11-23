"use client";

export default function SiteError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <main>
      <h1 className="font-display text-4xl">This page could not be shown</h1>
      <p className="mt-3 max-w-xl text-sm text-coral">{error.message || "Unknown error"}</p>
      <button type="button" onClick={reset} className="mt-4 rounded-full bg-amber px-4 py-2 text-sm font-semibold text-stone-950">
        Try again
      </button>
    </main>
  );
}
