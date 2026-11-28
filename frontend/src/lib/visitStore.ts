// Server-only visitor counter store. Uses a free Upstash Redis database over its REST API
// (no Neon, no card needed). If it is not configured, callers get `null` and the browser keeps
// its queued visits until it is.
import { createHash } from "node:crypto";

const URL_ = process.env.UPSTASH_REDIS_REST_URL || process.env.KV_REST_API_URL || "";
const TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN || process.env.KV_REST_API_TOKEN || "";

export const visitStoreConfigured = Boolean(URL_ && TOKEN);

type Cmd = (string | number)[];

async function pipeline(cmds: Cmd[]): Promise<unknown[] | null> {
  if (!visitStoreConfigured || cmds.length === 0) return null;
  const res = await fetch(`${URL_.replace(/\/$/, "")}/pipeline`, {
    method: "POST",
    headers: { Authorization: `Bearer ${TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify(cmds),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`visit store ${res.status}`);
  const out = (await res.json()) as { result?: unknown; error?: string }[];
  return out.map((r) => r.result ?? null);
}

/** One-way hash of the anonymous cookie id; the raw id and IP addresses are never stored. */
export function hashVisitor(id: string): string {
  const salt = process.env.VISIT_SALT || "sospana-sonke-visits";
  return createHash("sha256").update(`${salt}:${id}`).digest("hex").slice(0, 32);
}

export type Visit = { day: string; path: string };

export async function recordVisits(visitor: string, visits: Visit[]): Promise<boolean> {
  const cmds: Cmd[] = [["INCRBY", "visits:total", visits.length], ["PFADD", "visitors:all", visitor]];
  for (const v of visits) {
    cmds.push(["INCR", `visits:day:${v.day}`]);
    cmds.push(["PFADD", `visitors:day:${v.day}`, visitor]);
    cmds.push(["ZINCRBY", "visits:paths", 1, v.path]);
  }
  return (await pipeline(cmds)) !== null;
}

export function lastDays(n: number): string[] {
  const days: string[] = [];
  for (let i = 0; i < n; i++) days.push(saDay(new Date(Date.now() - i * 86400000)));
  return days;
}

/** Calendar day in South Africa time (YYYY-MM-DD). */
export function saDay(d: Date): string {
  return d.toLocaleDateString("en-CA", { timeZone: "Africa/Johannesburg" });
}

export async function readStats(days = 30) {
  const ds = lastDays(days);
  const cmds: Cmd[] = [["GET", "visits:total"], ["PFCOUNT", "visitors:all"], ["ZREVRANGE", "visits:paths", 0, 14, "WITHSCORES"]];
  for (const d of ds) {
    cmds.push(["GET", `visits:day:${d}`]);
    cmds.push(["PFCOUNT", `visitors:day:${d}`]);
  }
  const r = await pipeline(cmds);
  if (!r) return null;
  const paths: { path: string; views: number }[] = [];
  const pr = (r[2] as string[]) || [];
  for (let i = 0; i < pr.length; i += 2) paths.push({ path: pr[i], views: Number(pr[i + 1]) });
  return {
    total: Number(r[0] || 0),
    unique: Number(r[1] || 0),
    paths,
    daily: ds.map((day, i) => ({ day, views: Number(r[3 + i * 2] || 0), visitors: Number(r[4 + i * 2] || 0) })),
  };
}

/**
 * Public-safe totals for the visitor strip: counts only, no paths, no ids. `since` is the first
 * day (SAST) with a recorded view inside the last `lookbackDays`, so the label never claims a
 * start date the store cannot prove. Returns null when the store is not set up or has no views.
 */
export async function readPublicSummary(lookbackDays = 120) {
  const ds = lastDays(lookbackDays);
  const cmds: Cmd[] = [["GET", "visits:total"], ["PFCOUNT", "visitors:all"]];
  for (const d of ds) cmds.push(["GET", `visits:day:${d}`]);
  const r = await pipeline(cmds);
  if (!r) return null;
  const views = Number(r[0] || 0);
  const visitors = Number(r[1] || 0);
  if (!(views > 0) || !(visitors > 0)) return null;
  let since: string | null = null;
  for (let i = ds.length - 1; i >= 0; i--) {
    if (Number(r[2 + i] || 0) > 0) { since = ds[i]; break; }
  }
  return { views, visitors, since };
}
