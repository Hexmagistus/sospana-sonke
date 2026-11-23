"use client";

import { useState } from "react";
import type { Movie } from "@/lib/types";

export function TakedownForm({ movies }: { movies: Movie[] }) {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  return (
    <form
      className="grid max-w-xl gap-3"
      onSubmit={async (event) => {
        event.preventDefault();
        setPending(true);
        setError(null);
        setMessage(null);
        const form = new FormData(event.currentTarget);
        const response = await fetch("/api/takedown", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            claimantName: form.get("claimantName"),
            contactEmail: form.get("contactEmail"),
            contentId: form.get("contentId"),
            reason: form.get("reason"),
          }),
        });
        const body = (await response.json()) as { id?: string; error?: string; errors?: Record<string, string>; detail?: string };
        setPending(false);
        if (!response.ok) {
          setError(body.error || Object.values(body.errors ?? {}).join(" ") || "The complaint was not saved.");
          return;
        }
        setMessage(`Complaint ${body.id} was received. ${body.detail ?? ""}`);
        event.currentTarget.reset();
      }}
    >
      <label className="text-sm">
        Your name
        <input name="claimantName" required className="mt-1 w-full rounded-xl border border-white/15 bg-black/30 px-3 py-2" />
      </label>
      <label className="text-sm">
        Email
        <input name="contactEmail" type="email" required className="mt-1 w-full rounded-xl border border-white/15 bg-black/30 px-3 py-2" />
      </label>
      <label className="text-sm">
        Title
        <select name="contentId" required className="mt-1 w-full rounded-xl border border-white/15 bg-black/30 px-3 py-2" defaultValue="">
          <option value="" disabled>
            Choose a title
          </option>
          {movies.map((movie) => (
            <option key={movie.slug} value={movie.slug}>
              {movie.title}
            </option>
          ))}
        </select>
      </label>
      <label className="text-sm">
        What is the problem?
        <textarea name="reason" required minLength={20} rows={5} className="mt-1 w-full rounded-xl border border-white/15 bg-black/30 px-3 py-2" />
      </label>
      <button type="submit" disabled={pending} className="w-fit rounded-full bg-amber px-4 py-2 text-sm font-semibold text-stone-950" data-testid="takedown-submit">
        {pending ? "Sending…" : "Send complaint"}
      </button>
      {error ? <p className="text-sm text-coral" data-testid="takedown-error">{error}</p> : null}
      {message ? <p className="text-sm text-amber" data-testid="takedown-success">{message}</p> : null}
    </form>
  );
}
