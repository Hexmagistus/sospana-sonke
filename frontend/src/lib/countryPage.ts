/** Public country-page slugs. The snapshot supplies the names; this file only
turns a directory spelling into a stable URL piece and back. */

export function countrySlug(name: string): string {
  const folded = name.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const slug = folded.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return slug || "country";
}

/** One match, or null when the slug is unknown or two names would share it. */
export function countryFromSlug(slug: string, names: readonly string[]): string | null {
  const wanted = slug.trim().toLowerCase();
  if (!wanted) return null;
  const hits = names.filter((name) => countrySlug(name) === wanted);
  return hits.length === 1 ? hits[0] : null;
}

export function suggestCountries<T extends { name: string }>(
  query: string,
  rows: readonly T[],
  limit = 6,
): T[] {
  const needle = query.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
  if (!needle) return [];
  const prefix: T[] = [];
  const rest: T[] = [];
  for (const row of rows) {
    const folded = row.name.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    if (!folded.includes(needle)) continue;
    (folded.startsWith(needle) ? prefix : rest).push(row);
  }
  return [...prefix, ...rest].slice(0, limit);
}
