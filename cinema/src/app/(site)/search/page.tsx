import type { Metadata } from "next";
import { SearchScreen } from "@/components/search-screen";
import type { SearchQuery, SearchSort } from "@/lib/search";
import { getPublicCatalog } from "@/lib/public-catalog";

export const metadata: Metadata = {
  title: "Search",
  description: "Search the verified Sospana Cinema catalogue.",
  alternates: { canonical: "/search" },
};

const sorts: SearchSort[] = ["relevance", "title", "year", "runtime", "newest"];

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const one = (key: string) => {
    const value = params[key];
    return Array.isArray(value) ? value[0] : value;
  };
  const sort = one("sort");
  const initial: SearchQuery = {
    q: one("q") ?? "",
    country: one("country") || undefined,
    language: one("language") || undefined,
    genre: one("genre") || undefined,
    category: one("category") || undefined,
    yearFrom: numberOrUndefined(one("from")),
    yearTo: numberOrUndefined(one("to")),
    sort: sorts.includes(sort as SearchSort) ? (sort as SearchSort) : "relevance",
    kidsOnly: one("kids") === "1",
    playbackOnly: true,
  };
  const catalog = await getPublicCatalog();
  return (
    <main>
      <h1 className="font-display text-4xl">Search</h1>
      <p className="mt-2 max-w-2xl text-sm text-ink/70">Titles, people, countries and genres. A small typo still finds the closest title. Playback is listed only when a source was verified.</p>
      <div className="mt-6">
        <SearchScreen movies={catalog.movies} categories={catalog.categories} initial={initial} />
      </div>
    </main>
  );
}

function numberOrUndefined(value: string | undefined): number | undefined {
  if (!value) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}
