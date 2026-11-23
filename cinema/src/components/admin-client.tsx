"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Movie } from "@/lib/types";

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  return (
    <form
      className="grid max-w-sm gap-3"
      onSubmit={async (event) => {
        event.preventDefault();
        setPending(true);
        setError(null);
        const form = new FormData(event.currentTarget);
        const response = await fetch("/api/admin/login", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ email: form.get("email"), password: form.get("password") }),
        });
        const body = (await response.json()) as { error?: string };
        setPending(false);
        if (!response.ok) {
          setError(body.error || `Sign-in failed with HTTP ${response.status}.`);
          return;
        }
        router.push("/admin");
        router.refresh();
      }}
    >
      <label className="text-sm">
        Email
        <input name="email" type="email" autoComplete="username" required className="mt-1 w-full rounded-xl border border-white/15 bg-black/30 px-3 py-2" data-testid="admin-email" />
      </label>
      <label className="text-sm">
        Password
        <input name="password" type="password" autoComplete="current-password" required className="mt-1 w-full rounded-xl border border-white/15 bg-black/30 px-3 py-2" data-testid="admin-password" />
      </label>
      <button type="submit" disabled={pending} className="w-fit rounded-full bg-amber px-4 py-2 text-sm font-semibold text-stone-950" data-testid="admin-submit">
        {pending ? "Checking…" : "Sign in"}
      </button>
      {error ? <p className="text-sm text-coral" data-testid="admin-error">{error}</p> : null}
    </form>
  );
}

export function LogoutButton() {
  const router = useRouter();
  return (
    <button
      type="button"
      className="text-sm text-amber"
      onClick={async () => {
        await fetch("/api/admin/logout", { method: "POST" });
        router.push("/admin/login");
        router.refresh();
      }}
    >
      Sign out
    </button>
  );
}

export function MovieEditor({ movie }: { movie: Movie }) {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  return (
    <form
      className="grid max-w-xl gap-3"
      onSubmit={async (event) => {
        event.preventDefault();
        setError(null);
        const form = new FormData(event.currentTarget);
        const response = await fetch(`/api/admin/movies/${movie.slug}`, {
          method: "PATCH",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            title: form.get("title"),
            description: form.get("description"),
            country: form.get("country"),
            featured: form.get("featured") === "on",
            published: form.get("published") === "on",
            reviewStatus: form.get("reviewStatus") || undefined,
            ageSuitability: form.get("ageSuitability") || undefined,
            reviewNotes: form.get("reviewNotes") || undefined,
            playbackUrl: form.get("playbackUrl") || undefined,
            licenceEvidenceUrl: form.get("licenceEvidenceUrl") || undefined,
          }),
        });
        const body = (await response.json()) as { detail?: string; error?: string; errors?: Record<string, string> };
        if (!response.ok) {
          setError(body.error || Object.values(body.errors ?? {}).join(" ") || "The title was not saved.");
          return;
        }
        setMessage(body.detail || "Saved.");
      }}
    >
      <label className="text-sm">Title<input name="title" defaultValue={movie.title} className="mt-1 w-full rounded-xl border border-white/15 bg-black/30 px-3 py-2" /></label>
      <label className="text-sm">Description<textarea name="description" defaultValue={movie.description} rows={4} className="mt-1 w-full rounded-xl border border-white/15 bg-black/30 px-3 py-2" /></label>
      <label className="text-sm">Country<input name="country" defaultValue={movie.country} className="mt-1 w-full rounded-xl border border-white/15 bg-black/30 px-3 py-2" /></label>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="published" defaultChecked={movie.published} /> Published</label>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="featured" defaultChecked={movie.featured} /> Featured</label>
      <label className="text-sm">
        Kids review
        <select name="reviewStatus" defaultValue={movie.review?.reviewStatus ?? ""} className="mt-1 w-full rounded-xl border border-white/15 bg-black/30 px-3 py-2">
          <option value="">Leave unchanged</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
      </label>
      <label className="text-sm">
        Age group
        <select name="ageSuitability" defaultValue={movie.review?.ageSuitability ?? "not-for-kids"} className="mt-1 w-full rounded-xl border border-white/15 bg-black/30 px-3 py-2">
          <option value="preschool">Preschool</option>
          <option value="6-8">6–8</option>
          <option value="9-12">9–12</option>
          <option value="family">Family</option>
          <option value="not-for-kids">Not for kids</option>
        </select>
      </label>
      <label className="text-sm">Review notes<textarea name="reviewNotes" defaultValue={movie.review?.reviewNotes ?? ""} rows={3} className="mt-1 w-full rounded-xl border border-white/15 bg-black/30 px-3 py-2" /></label>
      <label className="text-sm">Add an authorized playback URL<input name="playbackUrl" placeholder="https://" className="mt-1 w-full rounded-xl border border-white/15 bg-black/30 px-3 py-2" /></label>
      <label className="text-sm">Licence evidence URL<input name="licenceEvidenceUrl" placeholder="https://" className="mt-1 w-full rounded-xl border border-white/15 bg-black/30 px-3 py-2" /></label>
      <button type="submit" className="w-fit rounded-full bg-amber px-4 py-2 text-sm font-semibold text-stone-950">Save</button>
      {error ? <p className="text-sm text-coral">{error}</p> : null}
      {message ? <p className="text-sm text-amber">{message}</p> : null}
    </form>
  );
}
