import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import {
  categoryLabel,
  checkedText,
  storedScopeText,
  urlScopeText,
  type PublicEmployer,
} from "@/lib/employerPage";
import { jobPosting } from "@/lib/jobPosting";
import { SITE_NAME, SITE_URL } from "@/lib/seo";

export const revalidate = 300;

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

type Load = PublicEmployer | null | "down";

async function loadEmployer(id: string): Promise<Load> {
  try {
    const res = await fetch(`${API}/employers/${encodeURIComponent(id)}`, { next: { revalidate: 300 } });
    if (res.status === 404) return null;
    if (!res.ok) return "down";
    const data = (await res.json()) as PublicEmployer;
    if (!data || typeof data.company_name !== "string" || typeof data.careers_url !== "string" || !data.careers_url) {
      return "down";
    }
    if (!Array.isArray(data.roles) || typeof data.open_role_count !== "number") return "down";
    return data;
  } catch {
    return "down";
  }
}

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const loaded = await loadEmployer(id);
  if (!loaded || loaded === "down") {
    return { title: "Employer" };
  }
  const description =
    `${loaded.company_name} (${loaded.country}): careers link, category, and open roles stored by ${SITE_NAME}. Apply on the employer's site.`;
  return {
    title: `${loaded.company_name} careers`,
    description,
    alternates: { canonical: `/employers/${loaded.id}` },
    openGraph: {
      title: `${loaded.company_name} careers · ${SITE_NAME}`,
      description,
      url: `/employers/${loaded.id}`,
    },
  };
}

export default async function EmployerPage({ params }: Props) {
  const { id } = await params;
  const loaded = await loadEmployer(id);
  if (loaded === null) notFound();
  if (loaded === "down") {
    return (
      <div className="ss-empty" role="status">
        <p className="text-base font-semibold text-ss-text">The directory is not answering</p>
        <p className="mt-2 max-w-lg text-sm leading-relaxed text-ss-muted">
          This page did not invent an employer or a list of roles.
        </p>
      </div>
    );
  }
  const employer = loaded;
  const category = categoryLabel(employer.source_type);
  const scope = urlScopeText(employer.careers_url);
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: SITE_NAME, item: SITE_URL },
      { "@type": "ListItem", position: 2, name: "Employers", item: `${SITE_URL}/employers` },
      { "@type": "ListItem", position: 3, name: employer.company_name, item: `${SITE_URL}/employers/${employer.id}` },
    ],
  };
  const rolesLd = employer.roles.length > 0
    ? {
        "@context": "https://schema.org",
        "@type": "ItemList",
        numberOfItems: employer.roles.length,
        itemListElement: employer.roles.map((role, index) => ({
          "@type": "ListItem",
          position: index + 1,
          item: jobPosting({
            ...role,
            title: role.title,
            company_name: employer.company_name,
            company_country: employer.country,
            employment_type: null,
            work_mode: null,
            salary: null,
            salary_min: null,
            salary_max: null,
            salary_currency: null,
            posting_date: null,
            is_open: true,
          }),
        })),
      }
    : null;

  return (
    <article className="mx-auto max-w-3xl space-y-6">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      {rolesLd ? (
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(rolesLd) }} />
      ) : null}
      <nav aria-label="Breadcrumb" className="text-sm text-ss-muted">
        <Link href="/" className="underline hover:text-ss-text">{SITE_NAME}</Link>
        <span aria-hidden="true"> · </span>
        <Link href="/employers" className="underline hover:text-ss-text">Employers</Link>
        <span aria-hidden="true"> · </span>
        <span className="text-ss-text">{employer.company_name}</span>
      </nav>
      <PageHeader eyebrow={category} title={employer.company_name}>
        <p>
          {employer.country}. {storedScopeText(employer.careers_scope)} You apply on the employer&apos;s site.{" "}
          {SITE_NAME} does not send an application for you.
        </p>
      </PageHeader>
      <section className="ss-card space-y-2">
        <h2 className="text-lg font-bold text-ss-text">Careers link</h2>
        <p className="text-sm text-ss-muted">{scope.label}. {scope.detail}</p>
        <p className="text-sm text-ss-muted">{checkedText(employer.last_checked, employer.url_looks_like_careers)}</p>
        <a
          href={employer.careers_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex text-sm font-semibold text-navy underline break-all"
        >
          {employer.careers_url}
        </a>
      </section>
      <section className="space-y-3">
        <h2 className="text-lg font-bold text-ss-text">
          Stored open roles ({employer.open_role_count.toLocaleString("en-US")}
          {employer.roles.length < employer.open_role_count ? `, showing ${employer.roles.length}` : ""})
        </h2>
        {employer.open_role_count === 0 ? (
          <p className="ss-empty text-sm text-ss-muted">
            No open role is stored for this employer. That does not mean the careers page is empty.
          </p>
        ) : (
          <ul className="grid gap-3">
            {employer.roles.map((role) => (
              <li key={role.id} className="ss-card">
                <h3 className="font-display text-xl font-bold text-ss-text">{role.title}</h3>
                <p className="mt-1 text-sm text-ss-muted">
                  {role.location ? `${role.location} · ` : ""}
                  Last seen on the employer site {role.last_seen_at.slice(0, 10)}
                  {role.closing_date ? ` · Closes ${role.closing_date}` : ""}
                </p>
                {role.application_url ? (
                  <a
                    href={role.application_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-3 inline-flex rounded-xl bg-navy px-4 py-2 text-sm font-semibold text-white"
                  >
                    Open on the employer site
                  </a>
                ) : (
                  <p className="mt-3 text-sm text-ss-muted">No application link was stored for this role.</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </article>
  );
}
