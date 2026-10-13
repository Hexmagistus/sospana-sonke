"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";

function VerifyForm() {
  const params = useSearchParams();
  const initial = params.get("token") || "";
  const [token, setToken] = useState(initial);
  const [message, setMessage] = useState("");
  const [done, setDone] = useState(false);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setMessage("");
    try {
      await api.post("/organisations/claims/verify", { token: token.trim() });
      setDone(true);
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "The link could not be confirmed.");
    }
  }

  return (
    <article className="mx-auto max-w-xl space-y-4">
      <h1 className="font-display text-3xl font-bold text-ss-text">Confirm your employer page</h1>
      {done ? (
        <p className="ss-card text-sm leading-relaxed text-ss-text" role="status">
          The domain email is confirmed. Open the organisation home to post an opportunity or correct a detail.
        </p>
      ) : (
        <form onSubmit={onSubmit} className="ss-card space-y-3">
          <label className="block text-sm font-semibold text-ss-text">
            Confirmation code
            <input
              value={token}
              onChange={(event) => setToken(event.target.value)}
              className="mt-1 w-full rounded-xl border border-ss-border bg-ss-surface px-3.5 py-2.5 text-sm text-ss-text"
              autoComplete="off"
              required
            />
          </label>
          <button type="submit" className="rounded-xl bg-gold px-4 py-2.5 text-sm font-semibold text-navy">
            Confirm
          </button>
          {message ? <p className="text-sm text-ss-muted" role="alert">{message}</p> : null}
        </form>
      )}
      <Link href="/organisation" className="text-sm font-semibold text-navy underline">
        Organisation home
      </Link>
    </article>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={<p className="text-sm text-ss-muted">Loading the confirmation form.</p>}>
      <VerifyForm />
    </Suspense>
  );
}
