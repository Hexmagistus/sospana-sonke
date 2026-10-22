import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { directoryPathFor, publicCountries, publicCountry, snapshotDateLabel } from "@/lib/countryPageData";
import { SITE_NAME, SITE_URL } from "@/lib/seo";

type Props = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return publicCountries().map((row) => ({ slug: row.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const row = publicCountry(slug);
  if (!row) return { title: "Country" };
  const description =
    `${row.name}: ${row.withLink.toLocaleString("en-US")} employers with a direct careers link ` +
    `in the ${SITE_NAME} directory on ${snapshotDateLabel()}. You apply on the employer's own page.`;
  return {
    title: `Careers pages in ${row.name}`,
    description,
    alternates: { canonical: `/countries/${row.slug}` },
    openGraph: {
      title: `Careers pages in ${row.name} · ${SITE_NAME}`,
      description,
      url: `/countries/${row.slug}`,
    },
  };
}

export default async function CountryPage({ params }: Props) {
  const { slug } = await params;
  const row = publicCountry(slug);
  if (!row) notFound();
  const directoryPath = directoryPathFor(row);
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: SITE_NAME, item: SITE_URL },
      { "@type": "ListItem", position: 2, name: "Countries", item: `${SITE_URL}/countries` },
      { "@type": "ListItem", position: 3, name: row.name, item: `${SITE_URL}/countries/${row.slug}` },
    ],
  };
  return (
    <article className="mx-auto max-w-3xl space-y-6">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <nav aria-label="Breadcrumb" className="text-sm text-ss-muted">
        <Link href="/" className="underline hover:text-ss-text">{SITE_NAME}</Link>
        <span aria-hidden="true"> · </span>
        <Link href="/countries" className="underline hover:text-ss-text">Countries</Link>
        <span aria-hidden="true"> · </span>
        <span className="text-ss-text">{row.name}</span>
      </nav>
      <header>
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-ss-text sm:text-4xl">
          {row.flag} Careers pages in {row.name}
        </h1>
        <p className="mt-3 text-base leading-relaxed text-ss-muted">
          The directory on {snapshotDateLabel()} lists {row.withLink.toLocaleString("en-US")} employers
          in {row.name} with a direct careers link. That count is employers, not open roles.
          A link is the employer&apos;s own careers page or their public applicant-system board.
          You apply there. We do not promise a place.
        </p>
      </header>
      <p className="ss-card text-sm leading-relaxed">
        Employers whose careers link is still being checked are in the full directory and are not
        part of this number.
      </p>
      <div className="flex flex-wrap gap-3">
        <Link
          href={directoryPath}
          className="inline-flex items-center rounded-xl bg-gold px-4 py-2.5 text-sm font-semibold text-navy shadow-sm ring-1 ring-navy/30"
        >
          Browse employers
        </Link>
        <Link
          href="/countries"
          className="inline-flex items-center rounded-xl border border-ss-border bg-ss-surface px-4 py-2.5 text-sm font-semibold text-ss-text"
        >
          All countries
        </Link>
      </div>
    </article>
  );
}
