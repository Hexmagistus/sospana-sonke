import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getPublicCatalog } from "@/lib/public-catalog";
import { currentAdmin } from "@/lib/session";

export const metadata: Metadata = { title: "Sources", robots: { index: false } };

export default async function SourcesPage() {
  const admin = await currentAdmin();
  if (!admin) redirect("/admin/login");
  const catalog = await getPublicCatalog();
  const counts = new Map<string, { available: number; other: number }>();
  for (const movie of catalog.movies) {
    for (const source of movie.sources) {
      const row = counts.get(source.providerId) ?? { available: 0, other: 0 };
      if (source.playbackStatus === "available") row.available += 1;
      else row.other += 1;
      counts.set(source.providerId, row);
    }
  }
  return (
    <main>
      <h1 className="font-display text-4xl">Sources</h1>
      <ul className="mt-6 space-y-3">
        {catalog.sources.map((source) => {
          const count = counts.get(source.id);
          return (
            <li key={source.id} className="rounded-2xl border border-white/10 p-4 text-sm">
              <p className="font-semibold">{source.providerName}</p>
              <p className="text-ink/60">{source.providerType} · {source.apiStatus}</p>
              <p className="mt-1">
                <a className="text-amber" href={source.websiteUrl}>{source.websiteUrl}</a>
              </p>
              <p className="mt-1">Terms: <a className="text-amber" href={source.termsReference}>{source.termsReference}</a></p>
              <p className="mt-1">{count?.available ?? 0} available playback rows, {count?.other ?? 0} not available.</p>
            </li>
          );
        })}
      </ul>
    </main>
  );
}
