/** World regions for the countries outside Africa, keyed by ISO 3166-1 alpha-2
code (XK = Kosovo). A static table: no service, no dependency.

The explorer sidebar shows South Africa, the rest of SADC and the rest of Africa
first (from directoryFilters), then these regions in this order. A country with
no entry lands in "Other", and worldRegions tests fail if any country in the
directory data is missing here, so a new country cannot hide there.

Judgement calls: Russia is listed under Europe and Turkey under Middle East.
Mexico is North America; the seven Central American states and the Caribbean
are their own group. Caucasus states (Armenia, Azerbaijan, Georgia) are Asia. */

export const WORLD_REGIONS = [
  { id: "europe", label: "Europe" },
  { id: "north-america", label: "North America" },
  { id: "central-america-caribbean", label: "Central America & Caribbean" },
  { id: "south-america", label: "South America" },
  { id: "asia", label: "Asia" },
  { id: "middle-east", label: "Middle East" },
  { id: "oceania", label: "Oceania" },
] as const;

export type WorldRegionId = (typeof WORLD_REGIONS)[number]["id"];

function codes(region: WorldRegionId, list: string): [string, WorldRegionId][] {
  return list.split(/\s+/).filter(Boolean).map((c) => [c, region]);
}

export const REGION_BY_CODE: Readonly<Record<string, WorldRegionId>> = Object.fromEntries([
  ...codes("europe", "AL AD AT BY BE BA BG HR CY CZ DK EE FI FR DE GR VA HU IS IE IT XK LV LI LT LU MT MD MC ME NL MK NO PL PT RO RU SM RS SK SI ES SE CH UA GB"),
  ...codes("north-america", "CA US MX GL BM"),
  ...codes("central-america-caribbean", "BZ CR SV GT HN NI PA AG BS BB CU DM DO GD HT JM KN LC VC TT PR"),
  ...codes("south-america", "AR BO BR CL CO EC GY PY PE SR UY VE"),
  ...codes("asia", "AF AM AZ BD BT BN KH CN GE HK IN ID JP KZ KG LA MO MY MV MN MM NP KP PK PH SG KR LK TW TJ TH TL TM UZ VN"),
  ...codes("middle-east", "BH IR IQ IL JO KW LB OM PS QA SA SY TR AE YE"),
  ...codes("oceania", "AU FJ KI MH FM NR NZ PW PG WS SB TO TV VU"),
]);

/** Region for an ISO code, or null when the table has no entry. */
export function worldRegionOf(code: string | null | undefined): WorldRegionId | null {
  return (code && REGION_BY_CODE[code.toUpperCase()]) || null;
}

/** Shown first inside a group, in this order, before the alphabetical rest. */
export const PINNED_FIRST: Readonly<Partial<Record<WorldRegionId, readonly string[]>>> = {
  "north-america": ["Canada", "United States", "Mexico"],
};
