import type { Metadata } from "next";
import Link from "next/link";
import { publicCountries, snapshotDateLabel, snapshotWithLinkTotal } from "@/lib/countryPageData";
import { SITE_NAME } from "@/lib/seo";

const dateLabel = snapshotDateLabel();
const total = snapshotWithLinkTotal();

export const metadata: Metadata = {
  title: "Employers by country",
  description:
    `${total.toLocaleString("en-US")} employers with a direct careers link, listed by country ` +
    `from the directory on ${dateLabel}. Sign in to open an employer and apply on their own page.`,
  alternates: { canonical: "/countries" },
  openGraph: {
    title: `Employers by country · ${SITE_NAME}`,
    description:
      `Country pages for employers with a direct careers link. Figures are the directory on ${dateLabel}.`,
    url: "/countries",
  },
};

export default function CountriesIndexPage() {
  const rows = publicCountries();
  return (
    <div className="space-y-6">
      <header className="max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-wide text-ss-muted">Directory</p>
        <h1 className="mt-1 font-display text-3xl font-extrabold tracking-tight text-ss-text sm:text-4xl">
          Employers by country
        </h1>
        <p className="mt-3 text-base leading-relaxed text-ss-muted">
          {total.toLocaleString("en-US")} employers with a direct careers link, across {rows.length} countries,
          from the directory on {dateLabel}. The full directory also lists employers whose link is still being
          checked. These pages do not list vacancies. Sign in to open an employer and apply on their site.
        </p>
      </header>
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {rows.map((row) => (
          <li key={row.slug}>
            <Link
              href={`/countries/${row.slug}`}
              className="flex min-h-14 items-center justify-between gap-3 rounded-2xl border border-ss-border bg-ss-surface px-4 py-3 text-ss-text shadow-sm transition hover:-translate-y-0.5 hover:border-navy"
            >
              <span className="font-semibold">{row.flag} {row.name}</span>
              <span className="shrink-0 text-sm tabular-nums text-ss-muted">
                {row.withLink.toLocaleString("en-US")}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
