/** Country and category rules for the signed-in directory.

A category click must leave the country alone. Only the country control
changes the country. "All" and "Listed" still need a real country, because
those two views are fetched one country at a time.
*/

export const DEFAULT_DIRECTORY_COUNTRY = "South Africa";

/** SADC members other than South Africa. Names match the directory spelling. */
const SADC_COUNTRIES = [
  "Angola", "Botswana", "Comoros", "DR Congo", "Eswatini", "Lesotho",
  "Madagascar", "Malawi", "Mauritius", "Mozambique", "Namibia", "Seychelles",
  "Tanzania", "Zambia", "Zimbabwe",
] as const;

/** The other African states, in the spelling the directory already uses. */
const OTHER_AFRICAN_COUNTRIES = [
  "Algeria", "Benin", "Burkina Faso", "Burundi", "Cabo Verde", "Cameroon",
  "Central African Republic", "Chad", "Congo", "Côte d'Ivoire", "Djibouti",
  "Egypt", "Equatorial Guinea", "Eritrea", "Ethiopia", "Gabon", "Gambia",
  "Ghana", "Guinea", "Guinea-Bissau", "Kenya", "Liberia", "Libya", "Mali",
  "Mauritania", "Morocco", "Niger", "Nigeria", "Rwanda", "Sao Tome and Principe",
  "Senegal", "Sierra Leone", "Somalia", "South Sudan", "Sudan", "Togo", "Tunisia",
  "Uganda",
] as const;

const COUNTRY_BAND = new Map<string, number>([
  [DEFAULT_DIRECTORY_COUNTRY, 0],
  ...SADC_COUNTRIES.map((name) => [name, 1] as const),
  ...OTHER_AFRICAN_COUNTRIES.map((name) => [name, 2] as const),
  // Older spellings still land in Africa if a row has not been renamed yet.
  ["Cape Verde", 2],
  ["Ivory Coast", 2],
  ["Cote dIvoire", 2],
  ["Republic of Congo", 2],
  ["São Tomé and Príncipe", 2],
]);

/** 0 South Africa, 1 other SADC, 2 other Africa, 3 everywhere else. */
export function countryBand(name: string): number {
  return COUNTRY_BAND.get(name) ?? 3;
}

/** South Africa, then the rest of SADC, then the rest of Africa, then other regions. */
export function compareCountries(a: string, b: string): number {
  const band = countryBand(a) - countryBand(b);
  if (band !== 0) return band;
  return a.localeCompare(b, "en");
}

export function sortCountries<T extends string>(names: readonly T[]): T[] {
  return [...names].sort(compareCountries);
}

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
