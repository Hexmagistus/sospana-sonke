import { NextResponse } from "next/server";
import { getPublicCatalog } from "@/lib/public-catalog";
import { rateLimit } from "@/lib/rate-limit";
import { searchMovies, type SearchSort } from "@/lib/search";

const sorts: SearchSort[] = ["relevance", "title", "year", "runtime", "newest"];

export async function GET(request: Request) {
  const ip = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "local";
  const limited = rateLimit(`search:${ip}`, 60, 60 * 1000);
  if (!limited.ok) {
    return NextResponse.json({ error: `Search is rate limited. Try again in ${limited.retryAfterSeconds} seconds.` }, { status: 429 });
  }
  const url = new URL(request.url);
  const sort = url.searchParams.get("sort") ?? "relevance";
  const catalog = await getPublicCatalog();
  const result = searchMovies(catalog.movies, {
    q: url.searchParams.get("q") ?? "",
    country: url.searchParams.get("country") || undefined,
    language: url.searchParams.get("language") || undefined,
    genre: url.searchParams.get("genre") || undefined,
    category: url.searchParams.get("category") || undefined,
    kidsOnly: url.searchParams.get("kids") === "1",
    playbackOnly: true,
    sort: sorts.includes(sort as SearchSort) ? (sort as SearchSort) : "relevance",
  });
  return NextResponse.json({
    corrected: result.corrected,
    hits: result.hits.slice(0, 40).map((hit) => ({
      slug: hit.movie.slug,
      title: hit.movie.title,
      year: hit.movie.releaseYear,
      country: hit.movie.country,
      score: hit.score,
    })),
  });
}
