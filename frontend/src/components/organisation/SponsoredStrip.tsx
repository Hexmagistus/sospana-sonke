import Link from "next/link";
import CountOutboundLink from "@/components/CountOutboundLink";
import type { PublicJob } from "@/lib/jobPosting";

/** A separate list. The caller keeps the organic rows in their existing order. */
export function SponsoredStrip({ jobs }: { jobs: PublicJob[] }) {
  if (!jobs.length) return null;
  return (
    <section aria-label="Sponsored" className="space-y-3">
      <div>
        <h2 className="text-lg font-bold text-ss-text">Sponsored</h2>
        <p className="mt-1 text-sm leading-relaxed text-ss-muted">
          These match the filters on this page. They do not change the order of the other rows.{" "}
          <Link href="/ranking" className="font-semibold text-navy underline">
            How ranking works
          </Link>
        </p>
      </div>
      <ul className="grid gap-3">
        {jobs.map((job) => (
          <li key={job.id} className="ss-card">
            <p className="text-sm font-semibold text-ss-primary">Sponsored</p>
            {job.employer_submitted ? (
              <p className="mt-1 text-sm text-ss-muted">Employer-submitted</p>
            ) : null}
            <h3 className="mt-1 font-display text-xl font-bold text-ss-text">{job.title}</h3>
            <p className="mt-1 text-sm text-ss-muted">
              {job.company_name}
              {job.company_country ? ` · ${job.company_country}` : ""}
              {job.location ? ` · ${job.location}` : ""}
            </p>
            {job.sponsored_until ? (
              <p className="mt-2 text-sm text-ss-muted">Paid placement runs until {job.sponsored_until.slice(0, 10)}.</p>
            ) : null}
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
    </section>
  );
}
