/**
 * Employer counts for the pre-login landing page.
 *
 * Live data comes from the public GET /companies/stats endpoint, which counts
 * employers that are active AND have a careers link (`with_link`,
 * `by_country_with_link`). Those are the employers the page can truthfully
 * call "a direct link to their own careers page".
 *
 * Until that answers (the free API sleeps), the page shows a snapshot taken
 * from the production database — see src/data/directory-snapshot.json for the
 * date and the exact rule. The last live answer is also kept in this browser,
 * so a returning visitor sees recent numbers straight away.
 */
import snapshot from "../data/directory-snapshot.json";
import { COUNTRY_FLAGS } from "./countryFlags";
import { NON_COUNTRY } from "./regions";

export type CountryRow = { name: string; flag: string; count: number };

export type LandingStats = {
  total: number;
  byCountry: Record<string, number>;
  /** "live" from the API, "cached" from this browser, "snapshot" built in. */
  source: "live" | "cached" | "snapshot";
};

export const SNAPSHOT_AS_OF: string = snapshot.as_of;

export function snapshotStats(): LandingStats {
  return {
    total: snapshot.with_link,
    byCountry: { ...(snapshot.by_country_with_link as Record<string, number>) },
    source: "snapshot",
  };
}

/**
 * Read the stats payload. Returns null unless it carries the direct-link
 * counts: an older API only has `employers` (every row, including ones with
 * no link yet), and showing that as "direct links" would overstate.
 */
export function parseStats(raw: unknown): LandingStats | null {
  if (!raw || typeof raw !== "object") return null;
  const data = raw as { with_link?: unknown; by_country_with_link?: unknown };
  if (typeof data.with_link !== "number" || !Number.isFinite(data.with_link) || data.with_link <= 0) return null;
  const map = data.by_country_with_link;
  if (!map || typeof map !== "object" || Array.isArray(map)) return null;
  const byCountry: Record<string, number> = {};
  for (const [name, n] of Object.entries(map as Record<string, unknown>)) {
    if (typeof n === "number" && Number.isFinite(n) && n > 0) byCountry[name] = Math.floor(n);
  }
  if (Object.keys(byCountry).length === 0) return null;
  return { total: Math.floor(data.with_link), byCountry, source: "live" };
}

const CACHE_KEY = "ss-landing-stats-v1";
const CACHE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;

export function readCachedStats(storage: Pick<Storage, "getItem"> | undefined, now = Date.now()): LandingStats | null {
  try {
    const text = storage?.getItem(CACHE_KEY);
    if (!text) return null;
    const saved = JSON.parse(text) as { at?: number; data?: unknown };
    if (typeof saved.at !== "number" || now - saved.at > CACHE_MAX_AGE_MS || now < saved.at) return null;
    const parsed = parseStats(saved.data);
    return parsed ? { ...parsed, source: "cached" } : null;
  } catch {
    return null;
  }
}

export function writeCachedStats(
  storage: Pick<Storage, "setItem"> | undefined,
  raw: unknown,
  now = Date.now(),
): void {
  try {
    if (!parseStats(raw)) return;
    storage?.setItem(CACHE_KEY, JSON.stringify({ at: now, data: raw }));
  } catch {
    /* private mode or full storage: the page still works without the cache */
  }
}

/** Real countries only, with a flag, biggest first (ties by name). */
export function countryRows(byCountry: Record<string, number>): CountryRow[] {
  return Object.entries(byCountry)
    .filter(([name, n]) => !NON_COUNTRY.has(name) && n > 0)
    .map(([name, count]) => ({ name, flag: COUNTRY_FLAGS[name] || "🌐", count }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name, "en"));
}
