import type { Metadata } from "next";
import { MovieCard } from "@/components/movies";
import { countryOptions } from "@/lib/countries";
import { getPublicCatalog } from "@/lib/public-catalog";

export const metadata: Metadata = {
  title: "Movies",
  description: "Every verified film and short in Sospana Cinema.",
  alternates: { canonical: "/movies" },
};

export default async function MoviesPage({ searchParams }: { searchParams: Promise<{ country?: string }> }) {
  const { country } = await searchParams;
  const catalog = await getPublicCatalog();
  const options = countryOptions(catalog.movies.map((movie) => movie.country));
  const movies = catalog.movies
    .filter((movie) => movie.published && (!country || movie.country === country))
    .sort((a, b) => a.title.localeCompare(b.title));
  return (
    <main>
      <h1 className="font-display text-4xl">Movies</h1>
      <p className="mt-3 max-w-2xl text-ink/75">The whole demonstration catalogue. South Africa is listed first in the country filter.</p>
      <form className="mt-4" action="/movies">
        <label className="text-sm">
          Country
          <select name="country" defaultValue={country ?? ""} className="ml-2 rounded-full border border-white/15 bg-black/30 px-3 py-2" aria-label="Country">
            <option value="">All countries</option>
            {options.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="ml-2 rounded-full bg-white/10 px-3 py-2 text-sm">
          Filter
        </button>
      </form>
      {movies.length === 0 ? <p className="mt-6 text-sm text-ink/70">No verified title is filed under that country.</p> : null}
      <div className="mt-6 flex flex-wrap gap-4">
        {movies.map((movie) => (
          <MovieCard key={movie.slug} movie={movie} />
        ))}
      </div>
    </main>
  );
}
