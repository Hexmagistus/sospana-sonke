/** Search and extra filters for the employer list already on screen.

These run in the browser on the slice the directory has loaded (one country,
or one category). They do not search the whole catalogue, and they do not
invent a remote or industry field the rows do not have.
*/

import { linkScope, type LinkScopeKind } from "./linkScope";

export type BoardFilter = "all" | "open" | "linked" | "blank";
export type ScopeFilter = "all" | Exclude<LinkScopeKind, "none">;

export type EmployerQueryRow = {
  company_name: string;
  jse_code?: string | null;
  careers_url?: string | null;
  open_vacancies?: number | null;
};

export function foldQuery(text: string): string {
  return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

export function matchesNameQuery(row: EmployerQueryRow, query: string): boolean {
  const needle = foldQuery(query);
  if (!needle) return true;
  return foldQuery(row.company_name).includes(needle) || foldQuery(row.jse_code || "").includes(needle);
}

/** "Open roles we counted" means a stored count above zero, not a guessed vacancy. */
export function matchesBoardFilter(row: EmployerQueryRow, filter: BoardFilter): boolean {
  const linked = !!(row.careers_url && row.careers_url.trim());
  if (filter === "linked") return linked;
  if (filter === "blank") return !linked;
  if (filter === "open") return (row.open_vacancies ?? 0) > 0;
  return true;
}

export function matchesScopeFilter(row: EmployerQueryRow, filter: ScopeFilter): boolean {
  if (filter === "all") return true;
  return linkScope(row.careers_url).kind === filter;
}

export function employerSuggestions(
  rows: readonly EmployerQueryRow[],
  query: string,
  limit = 8,
): string[] {
  const needle = foldQuery(query);
  if (!needle) return [];
  const prefix: string[] = [];
  const rest: string[] = [];
  const seen = new Set<string>();
  for (const row of rows) {
    const name = row.company_name.trim();
    if (!name) continue;
    const key = foldQuery(name);
    const code = foldQuery(row.jse_code || "");
    if (!key.includes(needle) && !code.includes(needle)) continue;
    if (seen.has(key)) continue;
    seen.add(key);
    (key.startsWith(needle) ? prefix : rest).push(name);
    if (prefix.length >= limit) break;
  }
  return [...prefix, ...rest].slice(0, limit);
}

export function refineIsNarrowed(query: string, board: BoardFilter, scope: ScopeFilter): boolean {
  return foldQuery(query).length > 0 || board !== "all" || scope !== "all";
}
