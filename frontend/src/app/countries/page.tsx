import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { publicCountries, snapshotDateLabel, snapshotWithLinkTotal } from "@/lib/countryPageData";
import { snapshotStats } from "@/lib/landingStats";
import { SITE_NAME } from "@/lib/seo";

const dateLabel = snapshotDateLabel();
const total = snapshotWithLinkTotal();

export const metadata: Metadata = {
  title: "Employers by country",
  description:
    `${total.toLocaleString("en-US")} employers with a direct careers link, listed by country ` +
    `from the directory on ${dateLabel}. Employers with a careers link also have a public page.`,
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
      <PageHeader eyebrow="Directory" title="Employers by country">
        <p>
          {total.toLocaleString("en-US")} employers with a direct careers link, across {rows.length} countries,
          from the directory on {dateLabel}. The full directory lists{" "}
          {(snapshotStats().directoryTotal ?? total).toLocaleString("en-US")} employers
          {snapshotStats().directoryCountries
            ? ` in ${snapshotStats().directoryCountries} countries`
            : ""}, including those whose link is still blank.
          These country pages do not list openings. Employers that already have a careers link also have a{" "}
          <Link href="/employers" className="underline">public page</Link>
          {" "}with that link and any roles the scanner has stored. Sign in to browse the full directory.
        </p>
      </PageHeader>
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {rows.map((row) => (
          <li key={row.slug}>
            <Link
              href={`/countries/${row.slug}`}
              className="ss-card flex min-h-14 items-center justify-between gap-3 !py-3 transition hover:-translate-y-0.5 hover:border-navy"
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
