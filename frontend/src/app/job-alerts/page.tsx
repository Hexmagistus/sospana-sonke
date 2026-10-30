import type { Metadata } from "next";
import data from "@/data/saCareers.json";
import type { CareersCat } from "@/components/CareersDirectory";
import { publicCountries } from "@/lib/countryPageData";
import JobAlertsHelper from "@/components/JobAlertsHelper";

export const metadata: Metadata = {
  title: "Job alerts helper | Sospana Sonke",
  description: "Pick employers, open their official careers portals, and track registering and switching on job alerts. Free, no login.",
};

export default function JobAlertsPage() {
  const seen = new Set<string>();
  const sa = (data as { categories: CareersCat[] }).categories
    .flatMap((c) => c.items)
    .filter((it) => (seen.has(it.u) ? false : (seen.add(it.u), true)))
    .map((it) => ({ a: it.a, n: it.n, u: it.u }));
  const countries = publicCountries()
    .filter((r) => r.slug !== "south-africa")
    .map((r) => ({ slug: r.slug, name: r.name, flag: r.flag }));
  return <JobAlertsHelper sa={sa} countries={countries} />;
}
