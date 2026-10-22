import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { publicCountries, publicCountry } from "@/lib/countryPageData";
import data from "@/data/countryCareers.json";
import CareersDirectory, { type CareersCat } from "@/components/CareersDirectory";
import { SITE_NAME } from "@/lib/seo";

type Props = { params: Promise<{ slug: string }> };
// Static snapshot built by scripts/build_country_careers.py (same rules as /sa-careers); no live DB.
const CAREERS = data as Record<string, { name: string; categories: CareersCat[] }>;

export const dynamicParams = false;

export function generateStaticParams() {
  return publicCountries().map((row) => ({ slug: row.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const row = publicCountry(slug);
  if (!row) return { title: "Country" };
  const description = `Direct careers links for employers in ${row.name}, free for everyone, no login needed.`;
  return {
    title: `${row.name} careers pages | ${SITE_NAME}`,
    description,
    alternates: { canonical: `/countries/${row.slug}` },
    openGraph: { title: `${row.name} careers pages · ${SITE_NAME}`, description, url: `/countries/${row.slug}` },
  };
}

export default async function CountryPage({ params }: Props) {
  const { slug } = await params;
  const row = publicCountry(slug);
  if (!row) notFound();
  const cats = CAREERS[row.slug]?.categories ?? [];
  return <CareersDirectory flag={row.flag} title={`${row.name} careers pages`} cats={cats} />;
}
