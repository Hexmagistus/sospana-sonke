/** Public role pages this device may keep for offline reading. Personal API responses stay out. */

export const RECENT_KEY = "ss-recent-roles";
export const OFFLINE_KEY = "ss-offline-roles";
export const OFFLINE_LIMIT = 8;

const ROLE_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export type OfflineRole = { id: string; title: string; company: string };

export function roleCachePath(id: string): string | null {
  if (!ROLE_ID.test(id)) return null;
  return `/jobs/${id}`;
}

export function readOfflineRoles(value: unknown): OfflineRole[] {
  if (!Array.isArray(value)) return [];
  const rows: OfflineRole[] = [];
  for (const row of value) {
    if (!row || typeof row !== "object") continue;
    const item = row as { id?: unknown; title?: unknown; company?: unknown; company_name?: unknown };
    if (typeof item.id !== "string" || !roleCachePath(item.id)) continue;
    const title = typeof item.title === "string" ? item.title.trim().slice(0, 160) : "";
    if (!title) continue;
    const companySource = typeof item.company === "string" ? item.company : item.company_name;
    const company = typeof companySource === "string" ? companySource.trim().slice(0, 80) : "";
    if (rows.some((kept) => kept.id === item.id)) continue;
    rows.push({ id: item.id, title, company });
    if (rows.length >= OFFLINE_LIMIT) break;
  }
  return rows;
}

export function rememberOfflineRole(existing: unknown, row: OfflineRole): OfflineRole[] {
  if (!roleCachePath(row.id) || !row.title.trim()) return readOfflineRoles(existing);
  const next = [
    { id: row.id, title: row.title.trim().slice(0, 160), company: row.company.trim().slice(0, 80) },
    ...readOfflineRoles(existing).filter((item) => item.id !== row.id),
  ];
  return next.slice(0, OFFLINE_LIMIT);
}

export function cacheRoleMessage(id: string): { type: "cache-role"; url: string } | null {
  const url = roleCachePath(id);
  if (!url) return null;
  return { type: "cache-role", url };
}
