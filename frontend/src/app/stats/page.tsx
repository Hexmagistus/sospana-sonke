import type { Metadata } from "next";
import { readStats, visitStoreConfigured } from "@/lib/visitStore";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Visitor stats", robots: { index: false, follow: false } };

export default async function StatsPage({ searchParams }: { searchParams: Promise<{ key?: string }> }) {
  const { key } = await searchParams;
  const expected = process.env.STATS_KEY;
  if (!expected || key !== expected) {
    return <p className="text-sm text-ss-muted">Visitor stats need the admin key: /stats?key=…</p>;
  }
  if (!visitStoreConfigured) {
    return <p className="text-sm">The visit store is not set up yet (UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN). Visits are waiting in visitors&apos; browsers.</p>;
  }
  let stats: Awaited<ReturnType<typeof readStats>> = null;
  try {
    stats = await readStats(30);
  } catch {
    stats = null;
  }
  if (!stats) return <p className="text-sm">Could not reach the visit store just now.</p>;
  return (
    <article className="mx-auto max-w-2xl space-y-4">
      <h1 className="font-display text-3xl font-bold">Visitor stats</h1>
      <p className="text-lg">
        <strong>{stats.total.toLocaleString()}</strong> page views · <strong>{stats.unique.toLocaleString()}</strong> unique visitors (all time, approx.)
      </p>
      <table className="w-full text-sm">
        <thead><tr className="text-left"><th>Day (SAST)</th><th>Views</th><th>Visitors</th></tr></thead>
        <tbody>
          {stats.daily.map((d) => (
            <tr key={d.day} className="border-t border-ss-border"><td>{d.day}</td><td>{d.views}</td><td>{d.visitors}</td></tr>
          ))}
        </tbody>
      </table>
      <h2 className="font-display text-xl font-bold">Top pages</h2>
      <ul className="text-sm">
        {stats.paths.map((p) => <li key={p.path}>{p.path}: {p.views}</li>)}
      </ul>
    </article>
  );
}
