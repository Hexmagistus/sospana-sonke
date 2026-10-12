import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { categoryLabel, employerPath, type PublicEmployerSummary } from "@/lib/employerPage";
import { SITE_NAME } from "@/lib/seo";

export const revalidate = 300;

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";
const PAGE = 50;

export const metadata: Metadata = {
  title: "Employers with a careers link",
  description:
    `Public pages for employers whose own careers link is stored by ${SITE_NAME}. Each page shows the link, when it was checked, and open roles the scanner has stored.`,
  alternates: { canonical: "/employers" },
  openGraph: {
    title: `Employers with a careers link · ${SITE_NAME}`,
    description: "Name, country, category, careers link and stored open roles. Employers without a careers link are not listed.",
    url: "/employers",
  },
};

type Load =
  | { ok: true; employers: PublicEmployerSummary[]; matched: number }
  | { ok: false };

async function loadPage(offset: number): Promise<Load> {
  try {
    const res = await fetch(`${API}/employers?limit=${PAGE}&offset=${offset}`, { next: { revalidate: 300 } });
    if (!res.ok) return { ok: false };
    const data = (await res.json()) as { employers?: PublicEmployerSummary[]; matched?: number };
    if (!data || !Array.isArray(data.employers) || typeof data.matched !== "number") return { ok: false };
    return { ok: true, employers: data.employers, matched: data.matched };
  } catch {
    return { ok: false };
  }
}

export default async function EmployersIndex({ searchParams }: { searchParams: Promise<{ offset?: string }> }) {
  const params = await searchParams;
  const parsed = Number(params.offset ?? "0");
  const offset = Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : 0;
  const loaded = await loadPage(offset);
  const from = offset + 1;
  const to = loaded.ok ? offset + loaded.employers.length : offset;
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Directory" title="Employers with a careers link">
        <p>
          These pages are only for employers that have a careers link stored. Each one shows the name,
          country, category, the link and when it was checked, and open roles the scanner has stored.
          You apply on the employer&apos;s site.
        </p>
      </PageHeader>
      {!loaded.ok ? (
        <div className="ss-empty" role="status">
          <p className="text-base font-semibold text-ss-text">The directory is not answering</p>
          <p className="mt-2 max-w-lg text-sm leading-relaxed text-ss-muted">
            No employer list was invented for this page.
          </p>
        </div>
      ) : loaded.matched === 0 ? (
        <p className="ss-empty text-sm text-ss-muted">No employer with a careers link is stored yet.</p>
      ) : (
        <>
          <p className="text-sm text-ss-muted">
            Showing {from.toLocaleString("en-US")}–{to.toLocaleString("en-US")} of {loaded.matched.toLocaleString("en-US")}.
            South Africa comes first, then the other SADC states, then the rest of Africa, then other regions.
          </p>
          <ul className="grid gap-3 sm:grid-cols-2">
            {loaded.employers.map((employer) => (
              <li key={employer.id}>
                <Link href={employerPath(employer.id)} className="ss-card block !py-3 hover:border-navy">
                  <span className="font-semibold text-ss-text">{employer.company_name}</span>
                  <span className="mt-1 block text-sm text-ss-muted">
                    {employer.country} · {categoryLabel(employer.source_type)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
          <nav aria-label="Employer pages" className="flex flex-wrap gap-4 text-sm font-semibold">
            {offset > 0 ? (
              <Link href={offset - PAGE > 0 ? `/employers?offset=${offset - PAGE}` : "/employers"} className="text-navy underline">
                Previous
              </Link>
            ) : null}
            {to < loaded.matched ? (
              <Link href={`/employers?offset=${offset + PAGE}`} className="text-navy underline">
                Next
              </Link>
            ) : null}
          </nav>
        </>
      )}
    </div>
  );
}
