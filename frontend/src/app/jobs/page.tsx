import type { Metadata } from "next";
import Link from "next/link";
import CountOutboundLink from "@/components/CountOutboundLink";
import { PageHeader } from "@/components/PageHeader";
import IntelligenceSearch from "@/components/home/IntelligenceSearch";
import { jobPosting, jobSummary, type PublicJob } from "@/lib/jobPosting";
import { SITE_NAME } from "@/lib/seo";

export const dynamic = "force-dynamic";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export const metadata: Metadata = {
  title: "Open roles the scanner has stored",
  description:
    "Search vacancies Sospana Sonke has already read from employer careers pages. Filter by country, employer, keyword and how recently the role was seen. Apply on the employer's site.",
  alternates: { canonical: "/jobs" },
  openGraph: {
    title: `Open roles · ${SITE_NAME}`,
    description:
      "Roles the scanner has stored. A missing role here does not mean the employer has no vacancies.",
    url: "/jobs",
  },
};

type Search = {
  q?: string;
  country?: string;
  employer?: string;
  freshness?: string;
};

type Load =
  | { ok: true; jobs: PublicJob[]; matched: number }
  | { ok: false };

function freshnessDays(value: string | undefined): string | null {
  if (value === "1" || value === "7" || value === "30") return value;
  return null;
}

async function loadJobs(search: Search): Promise<Load> {
  const params = new URLSearchParams();
  if (search.q?.trim()) params.set("q", search.q.trim().slice(0, 80));
  if (search.country?.trim()) params.set("country", search.country.trim().slice(0, 80));
  if (search.employer?.trim()) params.set("employer", search.employer.trim().slice(0, 80));
  const days = freshnessDays(search.freshness);
  if (days) params.set("max_age_days", days);
  try {
    const res = await fetch(`${API}/jobs?${params.toString()}`, { cache: "no-store" });
    if (!res.ok) return { ok: false };
    const data = (await res.json()) as { jobs?: PublicJob[]; matched?: number };
    if (!data || !Array.isArray(data.jobs) || typeof data.matched !== "number") return { ok: false };
    return { ok: true, jobs: data.jobs, matched: data.matched };
  } catch {
    return { ok: false };
  }
}

const fieldClass =
  "mt-1 w-full rounded-xl border border-ss-border bg-ss-surface px-3.5 py-2.5 text-sm text-ss-text placeholder:text-ss-muted";

export default async function JobsPage({ searchParams }: { searchParams: Promise<Search> }) {
  const search = await searchParams;
  const loaded = await loadJobs(search);
  const q = search.q ?? "";
  const country = search.country ?? "";
  const employer = search.employer ?? "";
  const freshness = freshnessDays(search.freshness) ?? "";
  const jsonLd = loaded.ok && loaded.jobs.length > 0
    ? {
        "@context": "https://schema.org",
        "@type": "ItemList",
        numberOfItems: loaded.jobs.length,
        itemListElement: loaded.jobs.map((job, index) => ({
          "@type": "ListItem",
          position: index + 1,
          item: jobPosting(job),
        })),
      }
    : null;

  return (
    <div className="space-y-6">
      {jsonLd ? (
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      ) : null}
      <PageHeader eyebrow="Vacancies" title="Open roles the scanner has stored">
        <p>
          These are jobs already saved from employer careers pages. The list is not every vacancy in a country.
          If nothing is here, the scanner has not stored a matching open role. Check the employer&apos;s own page.
          You apply there. {SITE_NAME} does not send an application for you.{" "}
          <Link href="/opportunities" className="font-semibold text-navy underline">
            Learnerships, bursaries and graduate programmes
          </Link>{" "}
          are listed separately.
        </p>
      </PageHeader>

      <IntelligenceSearch showAccountLinks={false} />

      <form method="get" action="/jobs" className="ss-card grid gap-4 sm:grid-cols-2">
        <label className="block text-sm font-semibold text-ss-text">
          Keyword
          <input name="q" defaultValue={q} placeholder="Title, for example nurse" className={fieldClass} />
        </label>
        <label className="block text-sm font-semibold text-ss-text">
          Country
          <input name="country" defaultValue={country} placeholder="South Africa" className={fieldClass} />
        </label>
        <label className="block text-sm font-semibold text-ss-text">
          Employer
          <input name="employer" defaultValue={employer} placeholder="Employer name" className={fieldClass} />
        </label>
        <label className="block text-sm font-semibold text-ss-text">
          Freshness
          <select name="freshness" defaultValue={freshness} className={fieldClass}>
            <option value="">Any time we last saw it</option>
            <option value="1">Last seen within a day</option>
            <option value="7">Last seen within 7 days</option>
            <option value="30">Last seen within 30 days</option>
          </select>
        </label>
        <div className="sm:col-span-2">
          <button
            type="submit"
            className="rounded-xl bg-gold px-5 py-2.5 text-sm font-semibold text-navy shadow-sm ring-1 ring-navy/30"
          >
            Search stored roles
          </button>
        </div>
      </form>

      {!loaded.ok ? (
        <div className="ss-empty" role="status">
          <p className="text-base font-semibold text-ss-text">The job index could not be reached</p>
          <p className="mt-2 max-w-lg text-sm leading-relaxed text-ss-muted">
            The directory of employer careers pages is still available. This page only lists roles the scanner has already stored.
          </p>
          <Link href="/countries" className="mt-4 inline-flex text-sm font-semibold text-navy underline">
            Browse employers by country
          </Link>
        </div>
      ) : loaded.matched === 0 ? (
        <div className="ss-empty" role="status">
          <p className="text-base font-semibold text-ss-text">No stored roles match</p>
          <p className="mt-2 max-w-lg text-sm leading-relaxed text-ss-muted">
            Nothing open in the scanner&apos;s index matches these filters. That can mean the index is empty, or that the wording differs.
            It does not mean those employers have no vacancies.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-ss-muted">
            Showing {loaded.jobs.length.toLocaleString("en-US")} of {loaded.matched.toLocaleString("en-US")} open roles that match.
          </p>
          <ul className="grid gap-3">
            {loaded.jobs.map((job) => (
              <li key={job.id} className="ss-card">
                <h2 className="font-display text-xl font-bold text-ss-text">{job.title}</h2>
                <p className="mt-1 text-sm text-ss-muted">
                  {job.company_id ? (
                    <Link href={`/employers/${job.company_id}`} className="font-semibold text-navy underline">
                      {job.company_name}
                    </Link>
                  ) : job.company_name}
                  {job.company_country ? ` · ${job.company_country}` : ""}
                  {job.location ? ` · ${job.location}` : ""}
                </p>
                <p className="mt-3 text-sm leading-relaxed text-ss-text">{jobSummary(job)}</p>
                <p className="mt-2 text-xs text-ss-muted">
                  Last seen on the employer site {job.last_seen_at.slice(0, 10)}
                  {job.closing_date ? ` · Closes ${job.closing_date}` : ""}
                </p>
                {job.application_url ? (
                  <CountOutboundLink
                    href={job.application_url}
                    targetKind="vacancy"
                    targetId={job.id}
                    className="mt-3 inline-flex min-h-11 items-center rounded-xl bg-navy px-4 py-2 text-sm font-semibold text-white"
                  >
                    Open on the employer site
                  </CountOutboundLink>
                ) : (
                  <p className="mt-3 text-sm text-ss-muted">No application link was stored for this role.</p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
