import { Suspense } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import IntelligenceSearch from "@/components/home/IntelligenceSearch";
import { ApplySteps } from "@/components/ApplySteps";
import { jobSummary, type PublicJob } from "@/lib/jobPosting";
import { SITE_NAME, SITE_URL } from "@/lib/seo";
import { RoleSuggestInput } from "@/components/RoleSuggestInput";
import { RecentRoles, SavedRoles } from "@/components/RoleExtras";
import { LIST_PAGE, listOffset } from "@/lib/listWindow";

export const dynamic = "force-dynamic";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

type Search = {
  q?: string;
  country?: string;
  employer?: string;
  freshness?: string;
  offset?: string;
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
  params.set("limit", String(LIST_PAGE));
  params.set("offset", String(listOffset(search.offset)));
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

function jobsHref(search: Search, offset: number): string {
  const params = new URLSearchParams();
  if (search.q?.trim()) params.set("q", search.q.trim());
  if (search.country?.trim()) params.set("country", search.country.trim());
  if (search.employer?.trim()) params.set("employer", search.employer.trim());
  const days = freshnessDays(search.freshness);
  if (days) params.set("freshness", days);
  if (offset > 0) params.set("offset", String(offset));
  const query = params.toString();
  return query ? `/jobs?${query}` : "/jobs";
}

async function JobResults({ search }: { search: Search }) {
  const loaded = await loadJobs(search);
  const offset = listOffset(search.offset);
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

  if (!loaded.ok) {
    return (
      <div className="ss-empty" role="status">
        <p className="text-base font-semibold text-ss-text">The role index could not be reached</p>
        <p className="mt-2 max-w-lg text-sm leading-relaxed text-ss-muted">
          The directory of employer careers pages is still available. This page only lists roles the scanner has already stored.
        </p>
        <Link href="/countries" className="mt-4 inline-flex text-sm font-semibold text-navy underline">
          Browse employers by country
        </Link>
      </div>
    );
  }
  if (loaded.matched === 0) {
    return (
      <div className="ss-empty" role="status">
        <p className="text-base font-semibold text-ss-text">No stored roles match</p>
        <p className="mt-2 max-w-lg text-sm leading-relaxed text-ss-muted">
          Nothing open in the scanner&apos;s index matches these filters. That can mean the index is empty, or that the wording differs.
          It does not mean those employers have nothing open.
        </p>
      </div>
    );
  }
  if (loaded.jobs.length === 0) {
    return (
      <div className="ss-empty" role="status">
        <p className="text-base font-semibold text-ss-text">This page is past the last stored role</p>
        <Link href={jobsHref(search, 0)} className="mt-4 inline-flex text-sm font-semibold text-[#0f766e] underline">
          Back to the first page
        </Link>
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {jsonLd ? (
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      ) : null}
      <p className="text-sm text-ss-muted">
        Showing {(offset + 1).toLocaleString("en-US")}–{(offset + loaded.jobs.length).toLocaleString("en-US")} of {loaded.matched.toLocaleString("en-US")} open roles that match.
      </p>
      <ul className="grid gap-3">
        {loaded.jobs.map((job) => (
          <li key={job.id} className="ss-card">
            <h2 className="font-display text-xl font-bold text-ss-text">
              <Link href={`/jobs/${job.id}`} className="underline">{job.title}</Link>
            </h2>
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
            <ApplySteps applicationUrl={job.application_url} vacancyId={job.id} />
          </li>
        ))}
      </ul>
      <nav aria-label="More stored roles" className="flex flex-wrap gap-4 text-sm">
        {offset > 0 ? (
          <Link href={jobsHref(search, offset - LIST_PAGE)} className="font-semibold text-[#0f766e] underline">
            Previous {LIST_PAGE}
          </Link>
        ) : null}
        {offset + loaded.jobs.length < loaded.matched ? (
          <Link href={jobsHref(search, offset + LIST_PAGE)} className="font-semibold text-[#0f766e] underline">
            Next {LIST_PAGE}
          </Link>
        ) : null}
      </nav>
    </div>
  );
}

export default async function JobsPage({ searchParams }: { searchParams: Promise<Search> }) {
  const search = await searchParams;
  const q = search.q ?? "";
  const country = search.country ?? "";
  const employer = search.employer ?? "";
  const freshness = freshnessDays(search.freshness) ?? "";

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Stored openings" title="Open roles the scanner has stored">
        <p>
          These are jobs, internships, learnerships, bursaries and graduate programmes already saved from official pages.
          The list is not every opening in a country.
          If nothing is here, the scanner has not stored a matching open role. Check the organisation&apos;s own page.
          You apply there. {SITE_NAME} does not send an application for you.{" "}
          <Link href="/opportunities" className="underline">
            The same list, with type tabs
          </Link>
          , sorts by closing date.
        </p>
      </PageHeader>

      <SavedRoles />
      <RecentRoles />
      <IntelligenceSearch showAccountLinks={false} />

      <form method="get" action="/jobs" className="ss-card ss-sticky-search grid gap-4 sm:grid-cols-2">
        <label className="block text-sm font-semibold text-ss-text">
          Keyword
          <RoleSuggestInput defaultValue={q} className={fieldClass} />
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
          <button type="submit" className="ss-intel-button min-h-11">
            Search stored roles
          </button>
        </div>
      </form>

      <Suspense fallback={<p className="text-sm text-ss-muted" role="status">Loading stored roles.</p>}>
        <JobResults search={search} />
      </Suspense>
    </div>
  );
}
