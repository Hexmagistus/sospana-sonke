import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ApplySteps } from "@/components/ApplySteps";
import { PageHeader } from "@/components/PageHeader";
import { countryFromSlug } from "@/lib/countryPage";
import type { PublicJob } from "@/lib/jobPosting";
import { SITE_NAME } from "@/lib/seo";

export const revalidate = 60;

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

type Facet = { name: string; count: number };
type Props = { params: Promise<{ country: string }> };

async function countryNames(): Promise<string[]> {
  try {
    const res = await fetch(`${API}/jobs/facets`, { next: { revalidate: 300 } });
    if (!res.ok) return [];
    const data = (await res.json()) as { countries?: Facet[] };
    return Array.isArray(data.countries) ? data.countries.map((row) => row.name).filter(Boolean) : [];
  } catch {
    return [];
  }
}

async function load(country: string): Promise<{ jobs: PublicJob[]; matched: number } | null> {
  try {
    const res = await fetch(`${API}/jobs?country=${encodeURIComponent(country)}&limit=30`, { next: { revalidate: 60 } });
    if (!res.ok) return null;
    const data = (await res.json()) as { jobs?: PublicJob[]; matched?: number };
    if (!data || !Array.isArray(data.jobs) || typeof data.matched !== "number") return null;
    return { jobs: data.jobs, matched: data.matched };
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { country: slug } = await params;
  const name = countryFromSlug(slug, await countryNames());
  if (!name) return { title: "Roles by country" };
  const loaded = await load(name);
  const count = loaded?.matched ?? 0;
  return {
    title: `Open stored roles in ${name}`,
    description: `${count.toLocaleString("en-US")} open roles ${SITE_NAME} has stored for ${name}. You apply on the source page.`,
    alternates: { canonical: `/jobs/in/${slug}` },
  };
}

export default async function JobsInCountry({ params }: Props) {
  const { country: slug } = await params;
  const names = await countryNames();
  const name = countryFromSlug(slug, names);
  if (!name) notFound();
  const loaded = await load(name);
  if (loaded && loaded.matched === 0) notFound();
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Stored openings" title={`Open roles in ${name}`}>
        <p>
          {loaded
            ? `${loaded.matched.toLocaleString("en-US")} open stored roles list ${name}.`
            : "The index could not be reached, so no count is shown."}{" "}
          This is not every opening in the country.
        </p>
      </PageHeader>
      {!loaded ? (
        <div className="ss-empty" role="status"><p className="font-semibold">The list could not be reached</p></div>
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
