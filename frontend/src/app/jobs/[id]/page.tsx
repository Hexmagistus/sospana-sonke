import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ApplySteps } from "@/components/ApplySteps";
import { PageHeader } from "@/components/PageHeader";
import { RememberRole, SaveRoleButton } from "@/components/RoleExtras";
import { jobPosting } from "@/lib/jobPosting";
import { CLOSED_OPPORTUNITY_HEADING, loadPublicJob } from "@/lib/loadPublicJob";
import { opportunityLabel } from "@/lib/opportunity";
import { SITE_NAME } from "@/lib/seo";

export const revalidate = 60;

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const job = await loadPublicJob(id);
  if (job === "down") {
    return { title: "Role index unavailable", robots: { index: false, follow: false } };
  }
  if (job === "closed") {
    return {
      title: CLOSED_OPPORTUNITY_HEADING,
      description: "This stored opportunity is no longer open. The record is kept, and it is not a live listing.",
      robots: { index: false, follow: false },
    };
  }
  if (!job) return { title: "Role not found" };
  const description = job.summary.slice(0, 180);
  return {
    title: `${job.title} at ${job.company_name}`,
    description,
    alternates: { canonical: `/jobs/${job.id}` },
    robots: { index: true, follow: true },
    openGraph: {
      title: `${job.title} · ${SITE_NAME}`,
      description,
      url: `/jobs/${job.id}`,
    },
  };
}

export default async function JobDetailPage({ params }: Props) {
  const { id } = await params;
  const job = await loadPublicJob(id);
  if (job === "down") {
    return (
      <div className="ss-empty" role="status">
        <p className="text-base font-semibold text-ss-text">The role index could not be reached</p>
        <p className="mt-2 text-sm text-ss-muted">Nothing was invented in its place.</p>
        <Link href="/jobs" className="mt-4 font-semibold text-[#0f766e] underline">Back to stored roles</Link>
      </div>
    );
  }
  if (job === "closed") {
    return (
      <article className="space-y-6">
        <PageHeader eyebrow="Closed" title={CLOSED_OPPORTUNITY_HEADING}>
          <p>The record is kept. It is not listed in search, and there is no application link here.</p>
        </PageHeader>
        <p>
          <Link href="/jobs" className="font-semibold text-[#0f766e] underline">Back to stored roles</Link>
        </p>
      </article>
    );
  }
  if (!job) notFound();
  const place = job.location || job.country || job.company_country;
  return (
    <article className="space-y-6">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jobPosting({ ...job, summary: job.summary })) }} />
      <RememberRole id={job.id} title={job.title} company={job.company_name} />
      <PageHeader eyebrow={opportunityLabel(job.opportunity_type)} title={job.title}>
        <p>
          {job.company_id ? (
            <Link href={`/employers/${job.company_id}`} className="underline">{job.company_name}</Link>
          ) : job.company_name}
          {place ? ` · ${place}` : ""}
        </p>
      </PageHeader>
      <section className="ss-card">
        <h2 className="text-lg font-bold text-ss-text">What was stored</h2>
        <p className="mt-2 text-base leading-relaxed text-ss-text">{job.summary}</p>
        <p className="mt-3 text-sm text-ss-muted">
          Last seen on the employer site {job.last_seen_at.slice(0, 10)}
          {job.closing_date ? ` · Closes ${job.closing_date}` : " · No closing date was stored"}
        </p>
        <ApplySteps applicationUrl={job.application_url} vacancyId={job.id} />
        <SaveRoleButton id={job.id} />
      </section>
    </article>
  );
}
