import type { Metadata } from "next";
import Link from "next/link";
import { SITE_NAME } from "@/lib/seo";

export const dynamic = "force-dynamic";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export const metadata: Metadata = {
  title: "Pricing for organisations",
  description:
    "Job seekers use Sospana Sonke for free. Organisation prices are in rand and stay unpublished until the owner sets them.",
  alternates: { canonical: "/pricing" },
};

type Plan = {
  code: string;
  label: string;
  amount_zar: number | null;
  price_status: string;
  owner_note: string;
  post_limit: number | null;
  duration_days: number | null;
  includes: string;
};

type Payload = {
  message: string | null;
  pricing_ready: boolean;
  plans: Plan[];
  checkout: { enabled: boolean; notice: string };
  seeker_note?: string;
};

async function loadPlans(): Promise<Payload | null> {
  try {
    const res = await fetch(`${API}/organisations/plans`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as Payload;
  } catch {
    return null;
  }
}

function priceLine(plan: Plan): string {
  if (plan.price_status === "included") return "Included. No charge.";
  if (plan.price_status === "set" && plan.amount_zar != null) {
    return `R${plan.amount_zar.toLocaleString("en-ZA")} ZAR`;
  }
  return "Pricing coming soon";
}

export default async function PricingPage() {
  const loaded = await loadPlans();
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header className="space-y-2">
        <p className="text-sm font-semibold text-ss-primary">Organisations</p>
        <h1 className="font-display text-3xl font-bold text-ss-text">Pricing</h1>
        <p className="text-sm leading-relaxed text-ss-muted">
          Search, alerts, and CV tools stay free for job seekers. These plans are for an organisation that wants to
          claim its page or place a labelled listing.
        </p>
      </header>

      {!loaded ? (
        <div className="ss-empty" role="status">
          <p className="text-base font-semibold text-ss-text">Pricing coming soon</p>
          <p className="mt-2 text-sm leading-relaxed text-ss-muted">
            The price list could not be reached. No amount is shown until the owner publishes one.
          </p>
        </div>
      ) : (
        <>
          {loaded.message ? (
            <p className="ss-card text-base font-semibold text-ss-text" role="status">
              {loaded.message}
            </p>
          ) : null}
          <ul className="grid gap-3">
            {loaded.plans.map((plan) => (
              <li key={plan.code} className="ss-card space-y-2">
                <h2 className="text-xl font-bold text-ss-text">{plan.label}</h2>
                <p className="text-base font-semibold text-ss-text">{priceLine(plan)}</p>
                {plan.price_status === "tbd" ? (
                  <p className="text-sm text-ss-muted">{plan.owner_note}</p>
                ) : null}
                <p className="text-sm leading-relaxed text-ss-text">{plan.includes}</p>
                {plan.post_limit != null ? (
                  <p className="text-sm text-ss-muted">Posts included: {plan.post_limit}. Every post is checked first.</p>
                ) : null}
                {plan.duration_days != null && plan.code !== "free" ? (
                  <p className="text-sm text-ss-muted">Paid window: {plan.duration_days} days, once a price is set.</p>
                ) : null}
              </li>
            ))}
          </ul>
          <p className="text-sm leading-relaxed text-ss-muted">{loaded.seeker_note}</p>
        </>
      )}

      <p className="text-sm text-ss-muted">
        <Link href="/for-organisations" className="font-semibold text-navy underline">
          Claim an employer page
        </Link>
        {" · "}
        <Link href="/ranking" className="font-semibold text-navy underline">
          How ranking works
        </Link>
        {" · "}
        <Link href="/" className="font-semibold text-navy underline">
          {SITE_NAME}
        </Link>
      </p>
    </div>
  );
}
