"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api, ApiError } from "@/lib/api";

type Summary = {
  currency: string;
  paid_zar: number;
  refunded_zar: number;
  net_zar: number;
  active_pro: number;
  active_featured: number;
  pending_claims: number;
  pending_posts: number;
  featured_slots: {
    id: string;
    vacancy_id: string | null;
    status: string;
    starts_at: string;
    ends_at: string;
  }[];
  plans: {
    code: string;
    label: string;
    amount_zar: number | null;
    amount_zar_raw?: number | null;
    published?: boolean;
    owner_note: string;
    post_limit: number | null;
    duration_days: number | null;
  }[];
  checkout: { enabled: boolean; mode: string; notice: string };
};

type Claim = {
  id: string;
  company_id: string;
  status: string;
  work_email: string;
  review_note: string | null;
};

type Post = {
  id: string;
  title: string;
  status: string;
  provenance: string;
  account_id: string;
  company_id: string;
};

function Desk() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [error, setError] = useState("");
  const [amounts, setAmounts] = useState<Record<string, string>>({});

  async function load() {
    const [next, nextClaims, nextPosts] = await Promise.all([
      api.get<Summary>("/admin/organisations/summary"),
      api.get<Claim[]>("/admin/organisations/claims"),
      api.get<Post[]>("/admin/organisations/posts"),
    ]);
    setSummary(next);
    setClaims(nextClaims);
    setPosts(nextPosts);
    const seeded: Record<string, string> = {};
    for (const plan of next.plans) {
      const raw = plan.amount_zar_raw ?? plan.amount_zar;
      seeded[plan.code] = raw == null ? "" : String(raw);
    }
    setAmounts(seeded);
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof ApiError ? err.message : "Could not load organisation admin."));
  }, []);

  async function savePlan(code: string, published: boolean) {
    setError("");
    const raw = (amounts[code] || "").trim();
    try {
      await api.patch(`/admin/organisations/plans/${code}`, raw === ""
        ? { clear_amount: true }
        : { amount_zar: Number(raw), published });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The price could not be saved.");
    }
  }

  async function moderate(kind: "claims" | "posts", id: string, approve: boolean) {
    setError("");
    try {
      await api.post(`/admin/organisations/${kind}/${id}`, { approve });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "That decision could not be saved.");
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-ss-text">Organisations</h1>
        <Link href="/admin" className="text-sm font-semibold text-navy underline">Admin dashboard</Link>
      </header>
      {error ? <p className="ss-card text-sm text-ss-text" role="alert">{error}</p> : null}
      {!summary ? <p className="text-sm text-ss-muted">Loading.</p> : (
        <>
          <section className="ss-card space-y-2" role="status">
            <h2 className="text-lg font-bold text-ss-text">Payments</h2>
            <p className="text-sm leading-relaxed text-ss-text">{summary.checkout.notice}</p>
            <p className="text-sm text-ss-muted">
              Paid {summary.currency} {summary.paid_zar.toLocaleString("en-ZA")}. Refunded {summary.refunded_zar.toLocaleString("en-ZA")}.
              Active Employer Pro {summary.active_pro}. Active featured slots {summary.active_featured}.
            </p>
          </section>

          <section className="ss-card space-y-3">
            <h2 className="text-lg font-bold text-ss-text">Prices</h2>
            <p className="text-sm text-ss-muted">
              Leave a paid plan blank to keep it as TBD by owner. The public page says Pricing coming soon until you publish an amount.
            </p>
            {summary.plans.map((plan) => (
              <form key={plan.code} className="grid gap-2 border-t border-ss-border pt-3 sm:grid-cols-[1fr_8rem_auto]" onSubmit={(event) => { event.preventDefault(); savePlan(plan.code, true); }}>
                <div>
                  <p className="text-sm font-semibold text-ss-text">{plan.label}</p>
                  <p className="text-sm text-ss-muted">{plan.owner_note}</p>
                </div>
                <label className="text-sm font-semibold text-ss-text">
                  ZAR
                  <input
                    inputMode="numeric"
                    className="mt-1 w-full rounded-xl border border-ss-border bg-ss-surface px-3 py-2 text-sm"
                    placeholder="TBD by owner"
                    value={amounts[plan.code] ?? ""}
                    onChange={(event) => setAmounts({ ...amounts, [plan.code]: event.target.value })}
                  />
                </label>
                <div className="flex items-end gap-2">
                  <button type="submit" className="rounded-xl bg-gold px-3 py-2 text-sm font-semibold text-navy">Publish</button>
                  <button type="button" className="rounded-xl bg-navy px-3 py-2 text-sm font-semibold text-white" onClick={() => savePlan(plan.code, false)}>Save hidden</button>
                </div>
              </form>
            ))}
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-bold text-ss-text">Claims ({summary.pending_claims} waiting)</h2>
            <ul className="grid gap-2">
              {claims.filter((row) => row.status === "pending_admin" || row.status === "pending_email").map((row) => (
                <li key={row.id} className="ss-card text-sm text-ss-text">
                  <p className="font-semibold">{row.work_email}</p>
                  <p className="text-ss-muted">{row.status.replaceAll("_", " ")} · {row.company_id}</p>
                  {row.review_note ? <p>{row.review_note}</p> : null}
                  <div className="mt-2 flex gap-2">
                    <button type="button" className="font-semibold text-navy underline" onClick={() => moderate("claims", row.id, true)}>Approve</button>
                    <button type="button" className="font-semibold text-navy underline" onClick={() => moderate("claims", row.id, false)}>Reject</button>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-bold text-ss-text">Employer posts ({summary.pending_posts} waiting)</h2>
            <ul className="grid gap-2">
              {posts.filter((row) => row.status === "pending").map((row) => (
                <li key={row.id} className="ss-card text-sm text-ss-text">
                  <p className="font-semibold">{row.title}</p>
                  <p className="text-ss-muted">{row.provenance} · {row.company_id}</p>
                  <div className="mt-2 flex gap-2">
                    <button type="button" className="font-semibold text-navy underline" onClick={() => moderate("posts", row.id, true)}>Approve</button>
                    <button type="button" className="font-semibold text-navy underline" onClick={() => moderate("posts", row.id, false)}>Reject</button>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-bold text-ss-text">Featured slots</h2>
            <ul className="grid gap-2">
              {summary.featured_slots.map((slot) => (
                <li key={slot.id} className="ss-card text-sm text-ss-text">
                  <p className="font-semibold">{slot.status}</p>
                  <p className="text-ss-muted">
                    {slot.vacancy_id || "No role"} · until {slot.ends_at.slice(0, 10)}
                  </p>
                </li>
              ))}
              {summary.featured_slots.length === 0 ? <li className="text-sm text-ss-muted">No featured slots yet.</li> : null}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}

export default function AdminOrganisationsPage() {
  return (
    <Guard admin>
      <Desk />
    </Guard>
  );
}
