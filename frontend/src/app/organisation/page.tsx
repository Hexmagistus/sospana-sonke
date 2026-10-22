"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Account = {
  id: string;
  company_id: string;
  status: string;
  method: string | null;
  work_email: string;
  public_blurb: string | null;
  contact_email: string | null;
  brand_headline: string | null;
  verification_token?: string | null;
};

type Me = {
  account: Account | null;
  post_limit: number | null;
  posts_used: number;
  pro: boolean;
  checkout: { enabled: boolean; notice: string; mode: string };
};

type Post = {
  id: string;
  title: string;
  status: string;
  provenance: string;
  vacancy_id: string | null;
  rejection_note: string | null;
};

type Plans = {
  message: string | null;
  plans: { code: string; label: string; price_status: string; amount_zar: number | null }[];
  checkout: { enabled: boolean; notice: string };
};

const field = "mt-1 w-full rounded-xl border border-ss-border bg-ss-surface px-3.5 py-2.5 text-sm text-ss-text";

export default function OrganisationHomePage() {
  const { user, loading } = useAuth();
  const [me, setMe] = useState<Me | null>(null);
  const [posts, setPosts] = useState<Post[]>([]);
  const [plans, setPlans] = useState<Plans | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [companyId, setCompanyId] = useState("");
  const [workEmail, setWorkEmail] = useState("");
  const [claimNote, setClaimNote] = useState("");
  const [post, setPost] = useState({
    title: "", description: "", application_url: "", opportunity_type: "job", location: "",
  });

  async function reload() {
    const next = await api.get<Me>("/organisations/me");
    setMe(next);
    if (next.account?.status === "verified") {
      setPosts(await api.get<Post[]>("/organisations/opportunities"));
    } else {
      setPosts([]);
    }
  }

  useEffect(() => {
    api.get<Plans>("/organisations/plans").then(setPlans).catch(() => setPlans(null));
  }, []);

  useEffect(() => {
    if (user?.role === "employer") {
      reload().catch((err) => setError(err instanceof ApiError ? err.message : "Could not load the organisation."));
    }
  }, [user]);

  async function claim(path: "/organisations/claims" | "/organisations/claims/admin") {
    setError("");
    setNotice("");
    try {
      const account = await api.post<Account>(path, {
        company_id: companyId.trim(),
        work_email: workEmail.trim(),
        note: claimNote.trim() || null,
      });
      if (account.status === "pending_admin") {
        setNotice("An administrator will check this claim.");
      } else {
        setNotice("Check the work inbox for the confirmation link. It expires in 48 hours.");
      }
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The claim could not be sent.");
    }
  }

  async function submitPost(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.post("/organisations/opportunities", post);
      setNotice("The opportunity is waiting for a check. It is not public yet.");
      setPost({ title: "", description: "", application_url: "", opportunity_type: "job", location: "" });
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The post could not be saved.");
    }
  }

  async function checkout(planCode: string, opportunityId?: string) {
    setError("");
    try {
      const started = await api.post<{ authorization_url?: string }>("/organisations/checkout", {
        plan_code: planCode,
        opportunity_id: opportunityId || null,
      });
      if (started.authorization_url) window.location.href = started.authorization_url;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Checkout is not available.");
    }
  }

  if (loading) return <p className="text-sm text-ss-muted">Loading your account.</p>;

  if (!user) {
    return (
      <article className="mx-auto max-w-xl space-y-3">
        <h1 className="font-display text-3xl font-bold text-ss-text">Organisation home</h1>
        <p className="text-sm text-ss-muted">Organisation pages are being reworked. Browse the public directory in the meantime.</p>
        <p className="text-sm"><Link href="/companies" className="font-semibold text-navy underline">Browse companies</Link></p>
      </article>
    );
  }

  if (user.role !== "employer") {
    return (
      <article className="mx-auto max-w-xl space-y-3">
        <h1 className="font-display text-3xl font-bold text-ss-text">Organisation home</h1>
        <p className="text-sm leading-relaxed text-ss-text">
          This area is for organisation accounts. A job-seeker account keeps search, alerts, and CV tools, and those stay free.
        </p>
        <Link href="/organisation/register" className="text-sm font-semibold text-navy underline">
          Create an organisation account
        </Link>
      </article>
    );
  }

  const checkoutOff = plans ? !plans.checkout.enabled : true;

  return (
    <article className="mx-auto max-w-3xl space-y-6">
      <header className="space-y-2">
        <h1 className="font-display text-3xl font-bold text-ss-text">Organisation home</h1>
        <p className="text-sm text-ss-muted">
          Signed in as {user.email}.{" "}
          <Link href="/pricing" className="font-semibold text-navy underline">Pricing</Link>
        </p>
      </header>
      {error ? <p className="ss-card text-sm text-ss-text" role="alert">{error}</p> : null}
      {notice ? <p className="ss-card text-sm text-ss-text" role="status">{notice}</p> : null}

      <section className="ss-card space-y-3">
        <h2 className="text-lg font-bold text-ss-text">Claim</h2>
        {me?.account ? (
          <p className="text-sm text-ss-text">
            Status: {me.account.status.replaceAll("_", " ")}
            {me.account.method ? ` · ${me.account.method.replaceAll("_", " ")}` : ""}. Company {me.account.company_id}.
          </p>
        ) : (
          <p className="text-sm text-ss-muted">No page is claimed on this account yet.</p>
        )}
        <label className="block text-sm font-semibold text-ss-text">
          Directory id
          <input className={field} value={companyId} onChange={(event) => setCompanyId(event.target.value)} />
        </label>
        <label className="block text-sm font-semibold text-ss-text">
          Work email on the employer domain
          <input type="email" className={field} value={workEmail} onChange={(event) => setWorkEmail(event.target.value)} />
        </label>
        <label className="block text-sm font-semibold text-ss-text">
          Note for an administrator
          <textarea className={field} value={claimNote} onChange={(event) => setClaimNote(event.target.value)} />
        </label>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="rounded-xl bg-gold px-4 py-2 text-sm font-semibold text-navy" onClick={() => claim("/organisations/claims")}>
            Confirm by domain email
          </button>
          <button type="button" className="rounded-xl bg-navy px-4 py-2 text-sm font-semibold text-white" onClick={() => claim("/organisations/claims/admin")}>
            Ask an administrator
          </button>
        </div>
      </section>

      {me?.account?.status === "verified" ? (
        <section className="ss-card space-y-3">
          <h2 className="text-lg font-bold text-ss-text">Opportunities</h2>
          <p className="text-sm text-ss-muted">
            {me.posts_used} of {me.post_limit ?? "the plan limit"} used. Each one is checked before it is listed and labelled employer-submitted.
            {me.pro ? " Employer Pro is active." : " Employer Pro is not active."}
          </p>
          <form onSubmit={submitPost} className="space-y-3">
            <label className="block text-sm font-semibold text-ss-text">
              Title
              <input className={field} value={post.title} onChange={(event) => setPost({ ...post, title: event.target.value })} required />
            </label>
            <label className="block text-sm font-semibold text-ss-text">
              Description
              <textarea className={field} value={post.description} onChange={(event) => setPost({ ...post, description: event.target.value })} required />
            </label>
            <label className="block text-sm font-semibold text-ss-text">
              Application link
              <input className={field} value={post.application_url} onChange={(event) => setPost({ ...post, application_url: event.target.value })} required />
            </label>
            <label className="block text-sm font-semibold text-ss-text">
              Location
              <input className={field} value={post.location} onChange={(event) => setPost({ ...post, location: event.target.value })} />
            </label>
            <button type="submit" className="rounded-xl bg-gold px-4 py-2 text-sm font-semibold text-navy">
              Submit for review
            </button>
          </form>
          <ul className="space-y-2">
            {posts.map((row) => (
              <li key={row.id} className="rounded-xl border border-ss-border px-3 py-2 text-sm text-ss-text">
                <p className="font-semibold">{row.title}</p>
                <p className="text-ss-muted">{row.status} · {row.provenance}</p>
                {row.status === "approved" ? (
                  <button type="button" className="mt-2 font-semibold text-navy underline" onClick={() => checkout("featured", row.id)}>
                    Feature this opportunity
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="ss-card space-y-2">
        <h2 className="text-lg font-bold text-ss-text">Checkout</h2>
        {checkoutOff ? (
          <p className="text-sm leading-relaxed text-ss-text" role="status">
            {plans?.checkout.notice || me?.checkout.notice || "Checkout is off until Paystack test keys and prices are set."}
          </p>
        ) : (
          <button type="button" className="rounded-xl bg-navy px-4 py-2 text-sm font-semibold text-white" onClick={() => checkout("pro")}>
            Continue to Paystack test checkout for Employer Pro
          </button>
        )}
        {plans?.message ? <p className="text-sm font-semibold text-ss-text">{plans.message}</p> : null}
        <ul className="text-sm text-ss-muted">
          {(plans?.plans || []).map((plan) => (
            <li key={plan.code}>
              {plan.label}: {plan.price_status === "set" && plan.amount_zar != null ? `R${plan.amount_zar}` : plan.price_status === "included" ? "Included" : "Pricing coming soon"}
            </li>
          ))}
        </ul>
      </section>
    </article>
  );
}
