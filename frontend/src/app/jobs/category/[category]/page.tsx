import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ApplySteps } from "@/components/ApplySteps";
import { PageHeader } from "@/components/PageHeader";
import { facetSlug } from "@/lib/jobLandings";
import type { PublicJob } from "@/lib/jobPosting";

export const revalidate = 60;

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

type Facet = { name: string; count: number };
type Props = { params: Promise<{ category: string }> };

async function categories(): Promise<Facet[]> {
  try {
    const res = await fetch(`${API}/jobs/facets`, { next: { revalidate: 300 } });
    if (!res.ok) return [];
    const data = (await res.json()) as { categories?: Facet[] };
    return Array.isArray(data.categories) ? data.categories : [];
  } catch {
    return [];
  }
}

function matchCategory(slug: string, rows: Facet[]): Facet | null {
  const hits = rows.filter((row) => facetSlug(row.name) === slug);
  return hits.length === 1 ? hits[0] : null;
}

async function load(name: string): Promise<{ jobs: PublicJob[]; matched: number } | null> {
  try {
    const res = await fetch(`${API}/jobs?employment_type=${encodeURIComponent(name)}&limit=30`, { next: { revalidate: 60 } });
    if (!res.ok) return null;
    const data = (await res.json()) as { jobs?: PublicJob[]; matched?: number };
    if (!data || !Array.isArray(data.jobs) || typeof data.matched !== "number") return null;
    return { jobs: data.jobs, matched: data.matched };
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { category } = await params;
  const row = matchCategory(category, await categories());
  if (!row) return { title: "Role category" };
  return {
    title: `${row.name} roles the scanner has stored`,
    description: `${row.count.toLocaleString("en-US")} open stored roles are filed as ${row.name}. You apply on the source page.`,
    alternates: { canonical: `/jobs/category/${category}` },
  };
}

export default async function JobsCategory({ params }: Props) {
  const { category } = await params;
  const row = matchCategory(category, await categories());
  if (!row) notFound();
  const loaded = await load(row.name);
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Stored openings" title={row.name}>
        <p>
          {loaded
            ? `${loaded.matched.toLocaleString("en-US")} open stored roles use this employment type.`
            : `${row.count.toLocaleString("en-US")} open stored roles use this employment type. The list could not be loaded.`}
        </p>
      </PageHeader>
      {!loaded || loaded.jobs.length === 0 ? (
        <div className="ss-empty" role="status">
          <p className="font-semibold text-ss-text">No stored role is listed for this type</p>
          <p className="mt-2 text-sm text-ss-muted">The index may be briefly unavailable. Browse all stored roles.</p>
          <Link href="/jobs" className="mt-3 inline-flex font-semibold text-[#0f766e] underline">All stored roles</Link>
        </div>
      ) : (
        <ul className="grid gap-3">
          {loaded.jobs.map((job) => (
            <li key={job.id} className="ss-card">
              <h2 className="font-display text-xl font-bold">
                <Link href={`/jobs/${job.id}`} className="underline">{job.title}</Link>
              </h2>
              <p className="mt-1 text-sm text-ss-muted">{job.company_name}</p>
              <ApplySteps applicationUrl={job.application_url} vacancyId={job.id} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
