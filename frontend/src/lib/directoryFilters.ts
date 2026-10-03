/** Country and category rules for the signed-in directory.

A category click must leave the country alone. Only the country control
changes the country. "All" and "Listed" still need a real country, because
those two views are fetched one country at a time.
*/

export const DEFAULT_DIRECTORY_COUNTRY = "South Africa";

export const DIRECTORY_COUNTRY_KEY = "ss-directory-country";

export const FILTER_TO_TYPE: Record<string, string> = {
  SOE: "SOE", Municipality: "MUNI", Department: "DEPT", Private: "PRIVATE", NGO: "NGO",
  University: "UNI", College: "COLLEGE", Hospital: "HOSPITAL", SETA: "SETA",
  Sports: "SPORT", Federations: "FED", Music: "MUSIC",
};

export const DIRECTORY_FILTERS = [
  "all", "listed", "SOE", "Municipality", "Department", "Private", "NGO",
  "University", "College", "Hospital", "SETA", "Sports", "Federations", "Music",
] as const;

export type DirectoryFilter = (typeof DIRECTORY_FILTERS)[number];

export const DIRECTORY_GUIDE_STEPS = [
  "Choose your country",
  "Pick a category",
  "Open an employer's careers link to see open vacancies",
  "Save or tailor your CV for roles you like",
] as const;

export function readStoredCountry(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(DIRECTORY_COUNTRY_KEY);
  } catch {
    return null;
  }
}

export function isDirectoryFilter(value: string | null): value is DirectoryFilter {
  return !!value && (DIRECTORY_FILTERS as readonly string[]).includes(value);
}

/** Country to keep after the user picks a category, All, or Listed. */
export function countryAfterFilterChange(country: string, filter: string): string {
  if (FILTER_TO_TYPE[filter]) return country;
  return country || DEFAULT_DIRECTORY_COUNTRY;
}

/**
 * Inbound ?type= does not clear the country. An explicit ?country= wins.
 * Otherwise the country already on screen (or the stored one) stays.
 */
export function countryFromDirectoryLink(input: {
  current: string;
  urlCountry: string | null;
  storedCountry: string | null;
}): string {
  if (input.urlCountry) return input.urlCountry;
  if (input.storedCountry !== null) return input.storedCountry;
  return input.current || DEFAULT_DIRECTORY_COUNTRY;
}

export function directorySliceKey(input: {
  shortlistKey: string | null;
  sourceType: string | null;
  country: string;
}): string {
  if (input.shortlistKey !== null) return `ids:${input.shortlistKey}`;
  if (input.sourceType) {
    return input.country
      ? `type:${input.sourceType}:country:${input.country}`
      : `type:${input.sourceType}`;
  }
  return `country:${input.country}`;
}

/** One scoped directory request. Category and country are sent together. */
export function directoryListPath(input: {
  ids?: string | null;
  sourceType?: string | null;
  country?: string;
}): string {
  if (input.ids) return `/companies?ids=${encodeURIComponent(input.ids)}&limit=200`;
  const params = new URLSearchParams();
  if (input.country) params.set("country", input.country);
  if (input.sourceType) params.set("source_type", input.sourceType);
  params.set("limit", "1500");
  return `/companies?${params.toString()}`;
}
