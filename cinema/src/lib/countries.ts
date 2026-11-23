/** South Africa, then the other SADC states, then the rest of Africa, then everywhere else. Alphabetical inside each band. */

export const SOUTH_AFRICA = "South Africa";

export const SADC = [
  "Angola",
  "Botswana",
  "Comoros",
  "Democratic Republic of the Congo",
  "Eswatini",
  "Lesotho",
  "Madagascar",
  "Malawi",
  "Mauritius",
  "Mozambique",
  "Namibia",
  "Seychelles",
  "Tanzania",
  "Zambia",
  "Zimbabwe",
] as const;

export const REST_OF_AFRICA = [
  "Algeria",
  "Benin",
  "Burkina Faso",
  "Burundi",
  "Cameroon",
  "Cape Verde",
  "Central African Republic",
  "Chad",
  "Congo",
  "Côte d'Ivoire",
  "Djibouti",
  "Egypt",
  "Equatorial Guinea",
  "Eritrea",
  "Ethiopia",
  "Gabon",
  "Gambia",
  "Ghana",
  "Guinea",
  "Guinea-Bissau",
  "Kenya",
  "Liberia",
  "Libya",
  "Mali",
  "Mauritania",
  "Morocco",
  "Niger",
  "Nigeria",
  "Rwanda",
  "São Tomé and Príncipe",
  "Senegal",
  "Sierra Leone",
  "Somalia",
  "South Sudan",
  "Sudan",
  "Togo",
  "Tunisia",
  "Uganda",
] as const;

const SADC_SET = new Set<string>(SADC);
const AFRICA_SET = new Set<string>(REST_OF_AFRICA);

export function countryBand(name: string): number {
  if (name === SOUTH_AFRICA) return 0;
  if (SADC_SET.has(name)) return 1;
  if (AFRICA_SET.has(name)) return 2;
  return 3;
}

export function isAfricanCountry(name: string): boolean {
  return countryBand(name) < 3;
}

export function sortCountries(names: readonly string[]): string[] {
  return [...names].sort((a, b) => countryBand(a) - countryBand(b) || a.localeCompare(b, "en"));
}

/** South Africa is always offered, even when the catalogue has no South African title yet. */
export function countryOptions(present: readonly string[]): string[] {
  return sortCountries(Array.from(new Set([SOUTH_AFRICA, ...present])));
}
