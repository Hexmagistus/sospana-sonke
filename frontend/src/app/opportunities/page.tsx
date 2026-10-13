import type { Metadata } from "next";
import Link from "next/link";
import CountOutboundLink from "@/components/CountOutboundLink";
import { ApplySteps } from "@/components/ApplySteps";
import type { PublicJob } from "@/lib/jobPosting";
import { PROGRAMME_PAGES } from "@/lib/jobLandings";
import { OPPORTUNITY_TABS, opportunityLabel, statedDate } from "@/lib/opportunity";
import { SITE_NAME, SITE_URL } from "@/lib/seo";

export const dynamic = "force-dynamic";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export const metadata: Metadata = {
  title: "Internships, learnerships, bursaries and graduate programmes",
  description:
    "Internships, learnerships, bursaries and graduate programmes Sospana Sonke has stored from official pages. A closing date is shown only when the source stated one. Jobs are in the same store.",
  alternates: { canonical: "/opportunities" },
  openGraph: {
    title: `Opportunities · ${SITE_NAME}`,
    description: "Stored programmes, with the type, the organisation, the source link and the last checked date.",
    url: "/opportunities",
  },
};

type Search = {
  type?: string;
  q?: string;
  sort?: string;
};

type Load = { ok: true; jobs: PublicJob[]; matched: number } | { ok: false };

const TYPES = new Set(OPPORTUNITY_TABS.map((tab) => tab.value).filter(Boolean));

function chosenType(value: string | undefined): string {
  const kind = (value || "").trim().toLowerCase().replace(/[-\s]+/g, "_");
  return TYPES.has(kind) ? kind : "";
}

async function loadJobs(search: Search): Promise<Load> {
  const params = new URLSearchParams();
  const kind = chosenType(search.type);
  if (kind) params.set("opportunity_type", kind);
  if (search.q?.trim()) params.set("q", search.q.trim().slice(0, 80));
  params.set("sort", search.sort === "checked" ? "checked" : "closing");
  params.set("limit", "30");
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

function tabHref(type: string, q: string, sort: string): string {
  const params = new URLSearchParams();
  if (type) params.set("type", type);
  if (q) params.set("q", q);
  if (sort === "checked") params.set("sort", "checked");
  const query = params.toString();
  return query ? `/opportunities?${query}` : "/opportunities";
}

export default async function OpportunitiesPage({ searchParams }: { searchParams: Promise<Search> }) {
  const search = await searchParams;
  const type = chosenType(search.type);
  const q = (search.q || "").trim();
  const sort = search.sort === "checked" ? "checked" : "closing";
  const loaded = await loadJobs({ type, q, sort });
  const jsonLd = loaded.ok && loaded.jobs.length > 0
    ? {
        "@context": "https://schema.org",
        "@type": "ItemList",
        numberOfItems: loaded.jobs.length,
        itemListElement: loaded.jobs.map((job, index) => ({
          "@type": "ListItem",
          position: index + 1,
          url: `${SITE_URL}/jobs/${job.id}`,
          name: job.title,
        })),
      }
    : null;

  return (
    <div className="space-y-6">
      {jsonLd ? (
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      ) : null}
      <header className="ss-hero ss-intel rounded-3xl px-5 py-8 sm:px-8">
        <p className="text-sm font-semibold uppercase tracking-wide ss-intel-accent">South Africa first</p>
        <h1 className="ss-intel-title mt-1 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
          Internships, learnerships, bursaries and graduate programmes
        </h1>
        <p className="ss-intel-lead mt-3 max-w-3xl text-base leading-relaxed">
          These are programmes already stored from an employer, a SETA, a university, or a government page.
          Jobs sit in the same list. A closing date appears only when that page stated one. If a date is not stated, the card says so.
          You apply on the source page. {SITE_NAME} does not send an application for you.
        </p>
      </header>

      <nav aria-label="Programme pages" className="flex flex-wrap gap-3 text-sm">
        {PROGRAMME_PAGES.map((page) => (
          <Link key={page.slug} href={`/opportunities/${page.slug}`} className="font-semibold text-[#0f766e] underline">
            {page.label}
          </Link>
        ))}
      </nav>

      <nav aria-label="Opportunity type" className="flex flex-wrap gap-2">
        {OPPORTUNITY_TABS.map((tab) => {
          const current = tab.value === type;
          return (
            <Link
              key={tab.label}
              href={tabHref(tab.value, q, sort)}
              aria-current={current ? "page" : undefined}
              className={
                current
                  ? "inline-flex min-h-11 items-center rounded-full bg-[#0c1b33] px-4 text-sm font-semibold text-white"
                  : "inline-flex min-h-11 items-center rounded-full border border-[#0c1b33]/20 bg-white px-4 text-sm font-semibold text-[#0c1b33]"
              }
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>

      <form method="get" action="/opportunities" className="ss-card ss-sticky-search flex flex-col gap-3 sm:flex-row sm:items-end">
        {type ? <input type="hidden" name="type" value={type} /> : null}
        <label className="block flex-1 text-sm font-semibold text-ss-text">
          Keyword
          <input name="q" defaultValue={q} placeholder="engineering, accounting" className="mt-1 w-full rounded-xl border border-ss-border bg-ss-surface px-3.5 py-2.5 text-sm text-ss-text" />
        </label>
        <label className="block text-sm font-semibold text-ss-text">
          Sort
          <select name="sort" defaultValue={sort} className="mt-1 w-full rounded-xl border border-ss-border bg-ss-surface px-3.5 py-2.5 text-sm text-ss-text">
            <option value="closing">Closing date</option>
            <option value="checked">Last checked</option>
          </select>
        </label>
        <button type="submit" className="ss-intel-button min-h-11">
          Show stored programmes
        </button>
      </form>

      {!loaded.ok ? (
        <div className="ss-empty" role="status">
          <p className="text-base font-semibold text-ss-text">The list could not be reached</p>
          <p className="mt-2 text-sm text-ss-muted">Employer careers pages are still in the directory.</p>
          <Link href="/countries" className="mt-4 inline-flex text-sm font-semibold text-[#0f766e] underline">
            Browse employers by country
          </Link>
        </div>
      ) : loaded.matched === 0 ? (
        <div className="ss-empty" role="status">
          <p className="text-base font-semibold text-ss-text">Not enough data</p>
          <p className="mt-2 max-w-lg text-sm leading-relaxed text-ss-muted">
            No stored programme matches these filters. That does not mean the organisation has no opening. Check the source page.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-ss-muted">
            Showing {loaded.jobs.length.toLocaleString("en-US")} of {loaded.matched.toLocaleString("en-US")}.
            {sort === "closing" ? " Closing dates that were not stated are listed last." : " Sorted by the date we last checked the row."}
          </p>
          <ul className="grid gap-3">
            {loaded.jobs.map((job) => (
              <li key={job.id} className="ss-intel-card border border-[#0c1b33]/10">
                <p className="text-sm font-semibold text-[#0f766e]">{opportunityLabel(job.opportunity_type)}</p>
                <h2 className="mt-1 font-display text-xl font-bold text-[#0c1b33]">
                  <Link href={`/jobs/${job.id}`} className="underline">{job.title}</Link>
                </h2>
                <p className="mt-1 text-sm text-[#3f4a5c]">
                  {job.company_id ? (
                    <Link href={`/employers/${job.company_id}`} className="font-semibold text-[#0c1b33] underline">
                      {job.company_name}
                    </Link>
                  ) : job.company_name}
                </p>
                <dl className="mt-3 grid gap-1 text-sm text-[#1c2430] sm:grid-cols-2">
                  <div>
                    <dt className="font-semibold">Closing date</dt>
                    <dd>{statedDate(job.closing_date)}</dd>
                  </div>
                  <div>
                    <dt className="font-semibold">Last checked</dt>
                    <dd>{statedDate(job.last_seen_at)}</dd>
                  </div>
                </dl>
                <ApplySteps applicationUrl={job.application_url} vacancyId={job.id} />
                {job.application_url ? (
                  <CountOutboundLink
                    href={job.application_url}
                    targetKind="vacancy"
                    targetId={job.id}
                    className="mt-3 inline-flex min-h-11 items-center rounded-xl bg-[#5eead4] px-4 py-2 text-sm font-semibold text-[#0c1b33]"
                  >
                    Source page
                  </CountOutboundLink>
                ) : (
                  <p className="mt-3 text-sm text-[#3f4a5c]">No source link was stored.</p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
