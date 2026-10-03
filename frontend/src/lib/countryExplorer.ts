/** Rows, groups and URL state for the country explorer (the split view on
/companies, /universities and /hospitals).

Order is the standing rule, always: South Africa, the rest of SADC, the rest of
Africa, then every other region. Counts are whatever the API sent; this file
never makes up a number. */

import { countryBand } from "./directoryFilters";
import { countryCode, countryFlag, resolveCountryParam } from "./countryCodes";
import { OTHER_AFRICA, SADC, TIERS, tierOf } from "./regions";

export type GroupId = "south-africa" | "sadc" | "africa" | "other";

export const GROUPS: readonly { id: GroupId; label: string }[] = [
  { id: "south-africa", label: "South Africa" },
  { id: "sadc", label: "Rest of SADC" },
  { id: "africa", label: "Rest of Africa" },
  { id: "other", label: "Other regions" },
];

export type CountryRow = {
  name: string;
  code: string | null;
  flag: string;
  /** Employers in the directory. 0 means none listed yet. */
  employers: number;
  withLinks: number;
  /** Employers whose vacancies we could count ("Not counted yet" is the rest). */
  counted: number;
  openVacancies: number;
  group: GroupId;
  /** False for a country with no employers: shown dimmed, not selectable. */
  selectable: boolean;
};

export type CountryInputs = {
  employers: Record<string, number>;
  withLinks?: Record<string, number>;
  counted?: Record<string, number>;
  openVacancies?: Record<string, number>;
};

export function groupOf(name: string): GroupId {
  if (name === "Africa") return "africa"; // Africa-wide bucket
  const band = countryBand(name);
  return band === 0 ? "south-africa" : band === 1 ? "sadc" : band === 2 ? "africa" : "other";
}

/** African states (not buckets) the explorer lists even when no employer is in yet. */
export const AFRICAN_COUNTRY_NAMES: readonly string[] = [
  "South Africa",
  ...Array.from(SADC),
  ...Array.from(OTHER_AFRICA).filter((n) => n !== "Africa"),
];

/** Fold case and accents so "cote" finds "Côte d'Ivoire". */
export function fold(text: string): string {
  return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

export function compareRows(a: CountryRow, b: CountryRow): number {
  const g = GROUPS.findIndex((x) => x.id === a.group) - GROUPS.findIndex((x) => x.id === b.group);
  return g || a.name.localeCompare(b.name, "en");
}

/**
 * One row per country with employers, plus the African states that have none
 * yet (dimmed, not selectable). Non-African countries with no employers are
 * not listed: the directory has no list of them to be honest about.
 */
export function buildCountryRows(input: CountryInputs, opts: { includeEmptyAfrican?: boolean } = {}): CountryRow[] {
  const names = new Set(Object.keys(input.employers).filter((n) => (input.employers[n] ?? 0) > 0));
  if (opts.includeEmptyAfrican) for (const n of AFRICAN_COUNTRY_NAMES) names.add(n);
  const rows = Array.from(names).map((name): CountryRow => {
    const employers = input.employers[name] ?? 0;
    return {
      name,
      code: countryCode(name),
      flag: countryFlag(name),
      employers,
      withLinks: input.withLinks?.[name] ?? 0,
      counted: input.counted?.[name] ?? 0,
      openVacancies: input.openVacancies?.[name] ?? 0,
      group: groupOf(name),
      selectable: employers > 0,
    };
  });
  return rows.sort(compareRows);
}

export type RowGroup = { id: GroupId; label: string; rows: CountryRow[] };

/** Groups in the fixed order. Empty groups are dropped; a search narrows rows. */
export function groupRows(rows: readonly CountryRow[], query = ""): RowGroup[] {
  const needle = fold(query);
  const match = (r: CountryRow) =>
    !needle || fold(r.name).includes(needle) || (r.code ?? "").toLowerCase() === needle;
  return GROUPS.map((g) => ({
    id: g.id,
    label: g.label,
    rows: rows.filter((r) => r.group === g.id && match(r)),
  })).filter((g) => g.rows.length > 0);
}

/** Number shown in the list heading: countries that actually have employers. */
export function listedCountryCount(rows: readonly CountryRow[]): number {
  return rows.filter((r) => r.selectable && r.name !== "Africa" && r.name !== "International").length;
}

/** "South Africa", "Rest of SADC", "Rest of Africa", or the world region ("Europe"). */
export function regionLabel(name: string): string {
  if (name === "Africa") return "Africa-wide";
  if (name === "International") return "International";
  const g = groupOf(name);
  if (g !== "other") return GROUPS.find((x) => x.id === g)!.label;
  const tier = TIERS.find((t) => t.id === tierOf(name));
  return tier && tier.id !== "other" ? tier.label : "Other regions";
}

/** Rows in the order a keyboard moves through them (selectable only). */
export function navigableRows(groups: readonly RowGroup[], collapsed: ReadonlySet<GroupId>, searching: boolean): CountryRow[] {
  return groups
    .filter((g) => searching || !collapsed.has(g.id))
    .flatMap((g) => g.rows)
    .filter((r) => r.selectable);
}

/** ?country=all is "All countries". A bare URL means "the default view", so Back can tell them apart. */
export const ALL_COUNTRIES_PARAM = "all";

/**
 * Read ?country=. Returns "" for All countries, a directory name for a code or
 * name, and null when the param is absent or matches nothing.
 */
export function countryFromQuery(raw: string | null | undefined, names: readonly string[]): string | null {
  const value = (raw ?? "").trim();
  if (!value) return null;
  if (value.toLowerCase() === ALL_COUNTRIES_PARAM) return "";
  return resolveCountryParam(value, names);
}

/**
 * Query string after the user picks a country. `country` is "" for All countries (?country=all).
 * Other params (like ?type=) stay; a ?company= deep link is dropped because the
 * user has now chosen a country themselves.
 */
export function searchForSelection(currentSearch: string, country: string): string {
  const params = new URLSearchParams(currentSearch.startsWith("?") ? currentSearch.slice(1) : currentSearch);
  params.delete("company");
  const code = country ? countryCode(country) : null;
  if (!country) params.set("country", ALL_COUNTRIES_PARAM);
  else if (code) params.set("country", code);
  else params.set("country", country);
  const out = params.toString();
  return out ? `?${out}` : "";
}
