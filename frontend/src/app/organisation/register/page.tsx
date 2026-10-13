"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function OrganisationRegisterPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [form, setForm] = useState({
    first_name: "", last_name: "", email: "", password: "", accepted_policy: false,
  });
  const [error, setError] = useState("");

  function set<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.post("/organisations/register", form);
      await login(form.email, form.password);
      router.push("/organisation");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The account could not be created.");
    }
  }

  const field = "mt-1 w-full rounded-xl border border-ss-border bg-ss-surface px-3.5 py-2.5 text-sm text-ss-text";

  return (
    <article className="mx-auto max-w-xl space-y-4">
      <h1 className="font-display text-3xl font-bold text-ss-text">Organisation account</h1>
      <p className="text-sm leading-relaxed text-ss-muted">
        This account is for an employer. It is not a job-seeker account. Job seekers register on the{" "}
        <Link href="/register" className="font-semibold text-navy underline">candidate page</Link>.
      </p>
      <form onSubmit={onSubmit} className="ss-card space-y-3">
        <label className="block text-sm font-semibold text-ss-text">
          First name
          <input className={field} value={form.first_name} onChange={(event) => set("first_name", event.target.value)} required />
        </label>
        <label className="block text-sm font-semibold text-ss-text">
          Last name
          <input className={field} value={form.last_name} onChange={(event) => set("last_name", event.target.value)} required />
        </label>
        <label className="block text-sm font-semibold text-ss-text">
          Email
          <input type="email" className={field} value={form.email} onChange={(event) => set("email", event.target.value)} required />
        </label>
        <label className="block text-sm font-semibold text-ss-text">
          Password
          <input type="password" minLength={8} className={field} value={form.password} onChange={(event) => set("password", event.target.value)} required />
        </label>
        <label className="flex items-start gap-2 text-sm text-ss-text">
          <input
            type="checkbox"
            checked={form.accepted_policy}
            onChange={(event) => set("accepted_policy", event.target.checked)}
            required
          />
          <span>
            I accept the <Link href="/terms" className="font-semibold text-navy underline">terms</Link> and the{" "}
            <Link href="/privacy" className="font-semibold text-navy underline">privacy policy</Link>.
          </span>
        </label>
        {error ? <p className="text-sm text-ss-muted" role="alert">{error}</p> : null}
        <button type="submit" className="rounded-xl bg-gold px-4 py-2.5 text-sm font-semibold text-navy">
          Create account
        </button>
      </form>
    </article>
  );
}
