/**
 * Region tiers for the landing page and the coverage map.
 *
 * Order is the standing rule: South Africa first, then the rest of SADC, then
 * the rest of Africa, then the other regions. Country spellings match the
 * directory (see backend app/services/country_names.py).
 */

export const TIERS = [
  { id: "south-africa", label: "South Africa", fill: "#ffe08a" },
  { id: "sadc", label: "Rest of SADC", fill: "#f5b301" },
  { id: "africa", label: "Rest of Africa", fill: "#c47d12" },
  { id: "oceania", label: "Oceania", fill: "#5fe0d0" },
  { id: "europe", label: "Europe", fill: "#8ec5ff" },
  { id: "south-america", label: "South America", fill: "#ff9e2c" },
  { id: "north-america", label: "North America", fill: "#c4b5fd" },
  { id: "asia", label: "Asia", fill: "#f0abfc" },
  { id: "other", label: "Other regions", fill: "#9fb3cc" },
] as const;

export type TierId = (typeof TIERS)[number]["id"];

export const TIER_RANK: Record<TierId, number> = Object.fromEntries(
  TIERS.map((t, i) => [t.id, i]),
) as Record<TierId, number>;

export const SADC = new Set([
  "Angola", "Botswana", "Comoros", "DR Congo", "Eswatini", "Lesotho",
  "Madagascar", "Malawi", "Mauritius", "Mozambique", "Namibia",
  "Seychelles", "Tanzania", "Zambia", "Zimbabwe",
]);

export const OTHER_AFRICA = new Set([
  "Algeria", "Benin", "Burkina Faso", "Burundi", "Cabo Verde", "Cameroon",
  "Central African Republic", "Chad", "Congo", "Côte d'Ivoire", "Djibouti",
  "Egypt", "Equatorial Guinea", "Eritrea", "Ethiopia", "Gabon", "Gambia",
  "Ghana", "Guinea", "Guinea-Bissau", "Kenya", "Liberia", "Libya", "Mali",
  "Mauritania", "Morocco", "Niger", "Nigeria", "Rwanda", "Sao Tome and Principe",
  "Senegal", "Sierra Leone", "Somalia", "South Sudan", "Sudan", "Togo", "Tunisia",
  "Uganda",
  // Directory buckets that are Africa-wide rather than one country.
  "Africa",
]);

const OCEANIA = new Set([
  "Australia", "New Zealand", "Fiji", "Papua New Guinea", "Samoa", "Tonga", "Solomon Islands", "Vanuatu",
  "Kiribati", "Marshall Islands", "Micronesia", "Nauru", "Palau", "Tuvalu",
]);
const EUROPE = new Set([
  "United Kingdom", "Germany", "France", "Netherlands", "Switzerland", "Sweden", "Denmark",
  "Finland", "Estonia", "Ireland", "Spain", "Belgium", "Italy", "Poland", "Austria",
  "Portugal", "Greece", "Czechia", "Czech Republic", "Hungary", "Romania", "Norway", "Ukraine",
  "Luxembourg", "Malta", "Cyprus", "Latvia", "Lithuania", "Iceland", "Slovakia", "Slovenia",
  "Bulgaria", "Croatia", "Serbia", "Albania", "Bosnia and Herzegovina", "North Macedonia",
  "Montenegro", "Kosovo", "Moldova", "Belarus", "Andorra", "Holy See", "Liechtenstein",
]);
const SOUTH_AMERICA = new Set([
  "Argentina", "Bolivia", "Brazil", "Chile", "Colombia", "Ecuador", "Guyana",
  "Paraguay", "Peru", "Suriname", "Uruguay", "Venezuela",
]);
const NORTH_AMERICA = new Set([
  "Canada", "United States", "United States of America", "Mexico", "Greenland",
  "Guatemala", "Belize", "Honduras", "El Salvador", "Nicaragua", "Costa Rica", "Panama",
  "Cuba", "Jamaica", "Haiti", "Dominican Republic", "Bahamas", "The Bahamas",
  "Trinidad and Tobago", "Barbados", "Puerto Rico",
  "Antigua and Barbuda", "Dominica", "Grenada", "Saint Kitts and Nevis", "Saint Lucia",
  "Saint Vincent and the Grenadines",
]);
// Russia and Turkey are shaded with Asia: most of each country is on that continent.
const ASIA = new Set([
  "India", "China", "Indonesia", "Iran", "United Arab Emirates", "Russia",
  "Japan", "South Korea", "North Korea", "Thailand", "Vietnam", "Malaysia", "Singapore",
  "Philippines", "Pakistan", "Bangladesh", "Sri Lanka", "Nepal", "Myanmar",
  "Saudi Arabia", "Qatar", "Kuwait", "Oman", "Yemen", "Iraq", "Israel", "Jordan",
  "Lebanon", "Syria", "Turkey", "Kazakhstan", "Uzbekistan", "Turkmenistan",
  "Kyrgyzstan", "Tajikistan", "Afghanistan", "Mongolia", "Taiwan", "Cambodia", "Laos",
  "Hong Kong", "Armenia", "Georgia", "Azerbaijan",
  "Bahrain", "Bhutan", "Brunei", "Maldives", "Palestine", "Timor-Leste",
]);

/** A directory name that is a bucket, not a country. */
export const NON_COUNTRY = new Set(["International", "Africa"]);

export function tierOf(name: string): TierId {
  if (name === "South Africa") return "south-africa";
  if (SADC.has(name)) return "sadc";
  if (OTHER_AFRICA.has(name)) return "africa";
  if (OCEANIA.has(name)) return "oceania";
  if (EUROPE.has(name)) return "europe";
  if (SOUTH_AMERICA.has(name)) return "south-america";
  if (NORTH_AMERICA.has(name)) return "north-america";
  if (ASIA.has(name)) return "asia";
  // An unmapped name is not guessed to be African.
  return "other";
}

export type CountRow = { name: string; count: number };

/** Employers and countries per tier, counting real countries only. */
export function tierTotals(rows: readonly CountRow[]): Record<TierId, { countries: number; employers: number }> {
  const out = Object.fromEntries(
    TIERS.map((t) => [t.id, { countries: 0, employers: 0 }]),
  ) as Record<TierId, { countries: number; employers: number }>;
  for (const row of rows) {
    if (row.count <= 0 || NON_COUNTRY.has(row.name)) continue;
    const t = out[tierOf(row.name)];
    t.countries += 1;
    t.employers += row.count;
  }
  return out;
}

const REGION_WORDS: Partial<Record<TierId, string>> = {
  oceania: "Oceania",
  europe: "Europe",
  "south-america": "South America",
  "north-america": "North America",
  asia: "Asia",
};

/**
 * "Africa, Oceania, Europe, South America, North America and Asia" — only the
 * regions that actually have employers, always in the standing order. Africa
 * comes first because the directory started there.
 */
export function coverageText(rows: readonly CountRow[]): string {
  const totals = tierTotals(rows);
  const names = ["Africa"];
  for (const t of TIERS) {
    const word = REGION_WORDS[t.id];
    if (word && totals[t.id].countries > 0) names.push(word);
  }
  if (names.length === 1) return names[0];
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}
