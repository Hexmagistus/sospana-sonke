import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ApplySteps } from "@/components/ApplySteps";
import { PageHeader } from "@/components/PageHeader";
import { programmeFromSlug } from "@/lib/jobLandings";
import type { PublicJob } from "@/lib/jobPosting";
import { SITE_NAME } from "@/lib/seo";

export const dynamic = "force-dynamic";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

type Props = { params: Promise<{ type: string }> };

async function load(type: string): Promise<{ jobs: PublicJob[]; matched: number } | null> {
  try {
    const res = await fetch(`${API}/jobs?opportunity_type=${encodeURIComponent(type)}&sort=closing&limit=30`, { cache: "no-store" });
    if (!res.ok) return null;
    const data = (await res.json()) as { jobs?: PublicJob[]; matched?: number };
    if (!data || !Array.isArray(data.jobs) || typeof data.matched !== "number") return null;
    return { jobs: data.jobs, matched: data.matched };
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { type } = await params;
  const page = programmeFromSlug(type);
  if (!page) return { title: "Programmes" };
  const loaded = await load(page.type);
  const count = loaded?.matched ?? 0;
  return {
    title: `${page.label} stored from official pages`,
    description: count > 0
      ? `${count.toLocaleString("en-US")} open ${page.label.toLowerCase()} Sospana Sonke has stored. You apply on the source page.`
      : `Open ${page.label.toLowerCase()} Sospana Sonke has stored. You apply on the source page.`,
    alternates: { canonical: `/opportunities/${page.slug}` },
    robots: loaded && count === 0 ? { index: false, follow: true } : undefined,
  };
}

export default async function ProgrammeLanding({ params }: Props) {
  const { type } = await params;
  const page = programmeFromSlug(type);
  if (!page) notFound();
  const loaded = await load(page.type);
  if (loaded && loaded.matched === 0) notFound();
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Stored programmes" title={page.label}>
        <p>
          {loaded
            ? `${loaded.matched.toLocaleString("en-US")} open ${page.label.toLowerCase()} are in the index right now.`
            : "The index could not be reached, so no count is shown."}{" "}
          This is not every {page.label.toLowerCase()} in the country. {SITE_NAME} does not send an application for you.
        </p>
      </PageHeader>
      {!loaded ? (
        <div className="ss-empty" role="status">
          <p className="font-semibold text-ss-text">The list could not be reached</p>
        </div>
      ) : (
        <ul className="grid gap-3">
          {loaded.jobs.map((job) => (
            <li key={job.id} className="ss-card">
              <h2 className="font-display text-xl font-bold">
                <Link href={`/jobs/${job.id}`} className="underline">{job.title}</Link>
              </h2>
              <p className="mt-1 text-sm text-ss-muted">{job.company_name}{job.company_country ? ` · ${job.company_country}` : ""}</p>
              <ApplySteps applicationUrl={job.application_url} vacancyId={job.id} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
