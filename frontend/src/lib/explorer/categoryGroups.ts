/** The explorer pages that list one group of directory categories.

The directory stores one category code per row (companies.source_type: UNI,
NGO, DEPT, ...). Each page below lists one group of codes, fetched with
GET /companies?group=<group>. The backend's single source of truth is
backend/app/services/category_groups.py; a backend test checks this file lists
the same codes per group. A group is only a filter: rows keep their own code
and still appear under it on /companies (state-owned entities stay findable
under "State-owned" there as well as on /government). */

export type CategoryType = {
  /** companies.source_type code. */
  code: string;
  /** Menu label, plural ("Municipalities"). */
  label: string;
  /** Lower-case plural for sentences ("municipalities or metros"). */
  noun: string;
  /** Card badge text, singular, with its icon. */
  badge: string;
  /** Badge colours (light/dark aware text utilities from globals.css). */
  badgeCls: string;
};

export type CategoryGroup = {
  /** Backend group name, also the ?group= value. */
  group: "universities" | "colleges" | "hospitals" | "ngos" | "government";
  path: string;
  /** Nav / landing label. */
  navLabel: string;
  /** Plural noun used in counts and headings ("NGOs & non-profits"). */
  noun: string;
  /** First entry of the category menu ("All colleges & SETAs"). */
  allLabel: string;
  /** Search placeholder noun ("NGO or charity"). */
  searchNoun: string;
  eyebrow: string;
  title: string;
  blurb: string;
  /** Landing page card line. */
  desc: string;
  icon: string;
  types: readonly CategoryType[];
};

export const CATEGORY_GROUPS: readonly CategoryGroup[] = [
  {
    group: "universities",
    path: "/universities",
    allLabel: "All universities",
    navLabel: "Universities",
    noun: "universities",
    searchNoun: "university",
    eyebrow: "Direct to institutions",
    title: "University vacancies",
    blurb: "Browse academic and support-staff openings and apply on each university's own careers page.",
    desc: "Academic & research posts",
    icon: "🎓",
    types: [{ code: "UNI", label: "Universities", noun: "universities", badge: "🎓 University", badgeCls: "bg-sky/10 text-sky" }],
  },
  {
    group: "colleges",
    path: "/colleges",
    allLabel: "All colleges & SETAs",
    navLabel: "Colleges & SETAs",
    noun: "colleges and SETAs",
    searchNoun: "college or SETA",
    eyebrow: "Direct to institutions",
    title: "Colleges & SETAs",
    blurb: "TVET, public and private colleges and the Sector Education and Training Authorities. Apply on each one's own careers page.",
    desc: "TVET & private colleges, SETAs",
    icon: "🏫",
    types: [
      { code: "COLLEGE", label: "Colleges (TVET, public & private)", noun: "colleges", badge: "🏫 College", badgeCls: "bg-teal/10 text-teal" },
      { code: "SETA", label: "SETAs", noun: "SETAs", badge: "🛠️ SETA", badgeCls: "bg-[#1a9e5f]/10 text-[#137a48]" },
    ],
  },
  {
    group: "hospitals",
    path: "/hospitals",
    allLabel: "All hospitals",
    navLabel: "Hospitals",
    noun: "hospitals",
    searchNoun: "hospital",
    eyebrow: "Direct to employers",
    title: "Hospital vacancies",
    blurb: "Browse hospital and healthcare-group openings and apply on each employer's own careers page.",
    desc: "Healthcare & clinical roles",
    icon: "🏥",
    types: [{ code: "HOSPITAL", label: "Hospitals", noun: "hospitals", badge: "🏥 Hospital", badgeCls: "bg-coral/10 text-coral" }],
  },
  {
    group: "ngos",
    path: "/ngos",
    allLabel: "All NGOs & non-profits",
    navLabel: "NGOs",
    noun: "NGOs and non-profits",
    searchNoun: "NGO, charity or agency",
    eyebrow: "Direct to organisations",
    title: "NGOs & non-profits",
    blurb: "NGOs, charities, non-profits and international organisations, including UN agencies. Apply on each one's own careers page.",
    desc: "NGOs, charities & UN agencies",
    icon: "🤝",
    types: [{ code: "NGO", label: "NGOs & non-profits", noun: "NGOs or non-profits", badge: "🤝 NGO / non-profit", badgeCls: "bg-coral/10 text-coral" }],
  },
  {
    group: "government",
    path: "/government",
    allLabel: "All public employers",
    navLabel: "Government",
    noun: "public employers",
    searchNoun: "department, municipality or SOE",
    eyebrow: "Direct to the public sector",
    title: "Government & public sector",
    blurb: "National and provincial departments, municipalities and metros, public agencies and state-owned entities. Apply on each one's own careers page.",
    desc: "Departments, municipalities & SOEs",
    icon: "🏛️",
    types: [
      { code: "DEPT", label: "Government departments", noun: "government departments", badge: "🏛️ Government department", badgeCls: "bg-navy/10 text-ss-text" },
      { code: "MUNI", label: "Municipalities & metros", noun: "municipalities or metros", badge: "Municipality", badgeCls: "bg-teal/10 text-teal" },
      { code: "SOE", label: "State-owned entities & agencies", noun: "state-owned entities or agencies", badge: "State-owned", badgeCls: "bg-purple/10 text-purple" },
    ],
  },
];

/** companies.source_type is String(10); the CSV import stores value.trim().toUpperCase().slice(0, 10). */
export const STORED_LENGTH = 10;

/** Other labels a row may be stored under -> the canonical code it is listed as.
 * Mirror of ALIASES in backend/app/services/category_groups.py (a backend test checks
 * they match). To support a new label, add the same line in both files. */
export const ALIASES: Readonly<Record<string, string>> = {
  // colleges
  "TVET": "COLLEGE",
  "TVET College": "COLLEGE",
  "Private College": "COLLEGE",
  "Public College": "COLLEGE",
  // ngos
  "NPO": "NGO",
  "NPC": "NGO",
  "Non-profit": "NGO",
  "Nonprofit": "NGO",
  "Charity": "NGO",
  "INGO": "NGO",
  "UN": "NGO",
  "Intl Org": "NGO",
  "IGO": "NGO",
  // government
  "Government": "DEPT",
  "Govt": "DEPT",
  "Department": "DEPT",
  "Ministry": "DEPT",
  "Provincial": "DEPT",
  "Municipality": "MUNI",
  "Metro": "MUNI",
  "Local Govt": "MUNI",
  "State-owned": "SOE",
  "Parastatal": "SOE",
  "Public Entity": "SOE",
  "Public Agency": "SOE",
};

/** How a category label is stored in companies.source_type (upper-case, 10 characters). */
export function storedCode(value: string | null | undefined): string {
  return (value || "").trim().toUpperCase().slice(0, STORED_LENGTH);
}

const ALIAS_TO_CODE: ReadonlyMap<string, string> = new Map(Object.entries(ALIASES).map(([k, v]) => [storedCode(k), v]));

/** The canonical code for a stored value: an alias maps to its code, anything else is unchanged (upper-cased). */
export function canonicalType(value: string | null | undefined): string {
  const key = storedCode(value);
  return ALIAS_TO_CODE.get(key) ?? key;
}

/** Nav / landing order: Companies first (its own page), then these. */
export const EXPLORER_NAV: readonly { href: string; label: string }[] = [
  { href: "/companies", label: "Companies" },
  ...CATEGORY_GROUPS.map((g) => ({ href: g.path, label: g.navLabel })),
];

export function groupByName(name: CategoryGroup["group"]): CategoryGroup {
  const g = CATEGORY_GROUPS.find((x) => x.group === name);
  if (!g) throw new Error(`Unknown category group: ${name}`);
  return g;
}

/** The group a source_type code belongs to (null for codes listed on /companies only). */
export function groupOfType(code: string | null | undefined): CategoryGroup | null {
  const c = canonicalType(code);
  return CATEGORY_GROUPS.find((g) => g.types.some((t) => t.code === c)) ?? null;
}

/** Badge for one row on a group page; an unexpected code still shows honestly. */
export function typeBadgeFor(group: CategoryGroup, code: string | null | undefined): { label: string; cls: string } {
  const c = canonicalType(code);
  const t = group.types.find((x) => x.code === c);
  return t ? { label: t.badge, cls: t.badgeCls } : { label: c || "Listed", cls: "bg-navy/10 text-ss-text" };
}

/** Rows per request. The API caps a signed-in user's scoped request at 1500 rows. */
export const PAGE_SIZE = 1500;
/** Safety stop for the paging loop (15,000 rows). */
export const MAX_PAGES = 10;

/** One page of a group's rows: active employers only, like the other explorer pages. */
export function groupListPath(group: CategoryGroup["group"], offset = 0): string {
  const params = new URLSearchParams({ group, active: "true", limit: String(PAGE_SIZE) });
  if (offset > 0) params.set("offset", String(offset));
  return `/companies?${params.toString()}`;
}

/** Fetches every page of a group (a group can exceed one request's cap). */
export async function fetchGroupRows<T>(group: CategoryGroup["group"], get: (path: string) => Promise<T[]>): Promise<T[]> {
  const out: T[] = [];
  for (let page = 0; page < MAX_PAGES; page++) {
    const rows = await get(groupListPath(group, page * PAGE_SIZE));
    out.push(...rows);
    if (rows.length < PAGE_SIZE) break;
  }
  return out;
}

/** Category menu for a group page: "All" plus one entry per code, counted for the scope shown. */
export function groupCategoryOptions(
  group: CategoryGroup,
  rows: readonly { source_type?: string | null; country?: string | null }[],
  country: string,
): { id: string; label: string; count: number }[] {
  const scoped = rows.filter((r) => !country || (r.country || "") === country);
  const count = (code: string) => scoped.filter((r) => canonicalType(r.source_type) === code).length;
  return [
    { id: "all", label: group.allLabel, count: scoped.length },
    ...group.types.map((t) => ({ id: t.code, label: t.label, count: count(t.code) })),
  ];
}

/** Honest empty-state copy: never fake rows, never "no jobs". */
export const NO_EMPLOYERS_YET = "No employers listed here yet";

type Row = { id: string; company_name: string; country?: string | null; source_type?: string | null; careers_url?: string | null };

/** Rows of the chosen category (all codes of the group for "all"). */
export function rowsInCategory<T extends Row>(rows: readonly T[], category: string): T[] {
  if (!category || category === "all") return [...rows];
  return rows.filter((r) => canonicalType(r.source_type) === category);
}

/** Cards shown: category, then country (or the shortlist), then the search; careers links first, then A-Z. */
export function shownRows<T extends Row>(rows: readonly T[], o: {
  category: string; country: string; q: string; shortlistOnly: boolean; shortlistIds: ReadonlySet<string>;
}): T[] {
  const needle = o.q.trim().toLowerCase();
  return rowsInCategory(rows, o.category)
    .filter((c) => o.shortlistOnly || !o.country || (c.country || "") === o.country)
    .filter((c) => !o.shortlistOnly || o.shortlistIds.has(c.id))
    .filter((c) => !needle || c.company_name.toLowerCase().includes(needle))
    .sort((a, b) => Number(!a.careers_url) - Number(!b.careers_url) || a.company_name.localeCompare(b.company_name));
}

/** What an empty card list says. Honest: an empty country is "not listed yet", never "no jobs". */
export function emptyStateFor(group: CategoryGroup, o: { shortlistOnly: boolean; q: string; country: string; category: string }): {
  icon: string; title: string; message: string;
} {
  if (o.shortlistOnly) return { icon: "⭐", title: "Your shortlist is empty", message: "Tap the ☆ on any card to add one." };
  if (o.q.trim()) return { icon: "🔍", title: "No matches", message: `No ${group.noun} match “${o.q.trim()}” here.` };
  const what = (o.category && o.category !== "all" && group.types.find((t) => t.code === o.category)?.noun) || group.noun;
  const where = o.country ? `in ${o.country}` : "in any country";
  return {
    icon: "🗺️",
    title: NO_EMPLOYERS_YET,
    message: `We have no ${what} ${where} in the directory yet. Try another country${group.types.length > 1 ? " or category" : ""}.`,
  };
}
