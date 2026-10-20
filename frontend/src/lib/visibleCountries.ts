/**
 * Countries the site shows (reversible focus filter, Oct 2026). Same lists as
 * backend/app/services/visible_countries.py — keep them identical.
 *
 * Kept: every country with English as an official language, every SADC member, every BRICS
 * member, plus the Africa / International buckets. Everything else is hidden from lists, maps,
 * counts and jobs. Nothing is deleted: the seed files, the database and
 * src/data/directory-snapshot.json keep every country.
 *
 * Undo: set HIDE_NON_ENGLISH_COUNTRIES to false here, point landingStats.ts and countryPageData.ts
 * back at "@/data/directory-snapshot.json", and set HIDE_NON_ENGLISH_COUNTRIES=0 on the API.
 * Regenerate the trimmed snapshot with: python3 scripts/build_visible_snapshot.py
 */

export const HIDE_NON_ENGLISH_COUNTRIES = true;

export const SADC_MEMBERS = [
  "South Africa", "Angola", "Botswana", "Comoros", "DR Congo", "Eswatini", "Lesotho", "Madagascar", "Malawi",
  "Mauritius", "Mozambique", "Namibia", "Seychelles", "Tanzania", "Zambia", "Zimbabwe",
] as const;

export const BRICS_MEMBERS = [
  "Brazil", "Russia", "India", "China", "South Africa", "Egypt", "Ethiopia", "Iran", "United Arab Emirates",
  "Indonesia",
] as const;

/** English is an official (de jure or de facto national) language. */
export const ENGLISH_OFFICIAL = [
  "South Africa", "Botswana", "Burundi", "Cameroon", "Eswatini", "Gambia", "Ghana", "Kenya", "Lesotho",
  "Liberia", "Malawi", "Mauritius", "Namibia", "Nigeria", "Rwanda", "Seychelles", "Sierra Leone",
  "South Sudan", "Sudan", "Tanzania", "Uganda", "Zambia", "Zimbabwe", "Saint Helena", "United Kingdom",
  "Ireland", "Malta", "Gibraltar", "United States", "Canada", "Antigua and Barbuda", "Bahamas", "Barbados",
  "Belize", "Dominica", "Grenada", "Guyana", "Jamaica", "Saint Kitts and Nevis", "Saint Lucia",
  "Saint Vincent and the Grenadines", "Trinidad and Tobago", "Anguilla", "Bermuda", "British Virgin Islands",
  "Cayman Islands", "Montserrat", "Turks and Caicos Islands", "US Virgin Islands", "Puerto Rico",
  "Falkland Islands", "Sint Maarten", "Curaçao", "Caribbean Netherlands", "India", "Pakistan", "Philippines",
  "Singapore", "Hong Kong", "Australia", "New Zealand", "Fiji", "Papua New Guinea", "Samoa", "Tonga",
  "Solomon Islands", "Vanuatu", "Kiribati", "Marshall Islands", "Micronesia", "Nauru", "Palau", "Tuvalu",
  "Cook Islands", "Niue", "American Samoa", "Guam", "Northern Mariana Islands",
] as const;

export const VISIBLE_COUNTRIES: ReadonlySet<string> = new Set<string>([
  ...SADC_MEMBERS, ...BRICS_MEMBERS, ...ENGLISH_OFFICIAL, "Africa", "International",
]);

/** Blank names are never hidden. */
export function isVisibleCountry(name: string | null | undefined): boolean {
  return !HIDE_NON_ENGLISH_COUNTRIES || !name || VISIBLE_COUNTRIES.has(name);
}

export function visibleCounts<T>(byCountry: Record<string, T>): Record<string, T> {
  if (!HIDE_NON_ENGLISH_COUNTRIES) return byCountry;
  return Object.fromEntries(Object.entries(byCountry).filter(([name]) => isVisibleCountry(name)));
}
