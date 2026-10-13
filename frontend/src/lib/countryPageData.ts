/** Countries that have a public page. Counts are the built-in with-link snapshot,
the same figures the homepage shows before the live directory answers. */

import snapshot from "@/data/directory-snapshot.json";
import { countryFlag, countryCode } from "@/lib/countryCodes";
import { countryFromSlug, countrySlug } from "@/lib/countryPage";
import { compareCountries } from "@/lib/directoryFilters";
import { snapshotAsOfLabel } from "@/lib/landingStats";
import { NON_COUNTRY } from "@/lib/regions";

export type PublicCountry = {
  name: string;
  slug: string;
  flag: string;
  code: string | null;
  withLink: number;
};

export function publicCountries(): PublicCountry[] {
  const counts = snapshot.by_country_with_link as Record<string, number>;
  return Object.entries(counts)
    .filter(([name, count]) => count > 0 && !NON_COUNTRY.has(name))
    .map(([name, withLink]) => ({
      name,
      slug: countrySlug(name),
      flag: countryFlag(name),
      code: countryCode(name),
      withLink,
    }))
    .sort((a, b) => compareCountries(a.name, b.name));
}

export function publicCountry(slug: string): PublicCountry | null {
  const rows = publicCountries();
  const name = countryFromSlug(slug, rows.map((row) => row.name));
  return rows.find((row) => row.name === name) ?? null;
}

export function snapshotWithLinkTotal(): number {
  return snapshot.with_link;
}

export function snapshotDateLabel(): string {
  return snapshotAsOfLabel(snapshot.as_of);
}

/** Path inside the signed-in directory for this country, when we have a code. */
export function directoryPathFor(country: PublicCountry): string {
  return country.code ? `/companies?country=${country.code}` : "/companies";
}
