import Link from "next/link";
import { ContinueRow } from "@/components/continue-row";
import { MovieRow, Poster } from "@/components/movies";
import { isApprovedForKids, moviesInCategory, canWatch } from "@/lib/catalog";
import { getPublicCatalog } from "@/lib/public-catalog";
import type { Movie } from "@/lib/types";
import { formatRuntime, siteUrl } from "@/lib/utils";

function pick(catalogMovies: Movie[], slugs: string[]): Movie[] {
  return slugs.flatMap((slug) => {
    const movie = catalogMovies.find((item) => item.slug === slug);
    return movie ? [movie] : [];
  });
}

export default async function HomePage() {
  const catalog = await getPublicCatalog();
  const hero = catalog.movies.find((movie) => movie.slug === catalog.heroSlug) ?? catalog.movies[0];
  const watch = hero ? canWatch(hero) : false;
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "SOSPANA CINEMA",
    url: siteUrl(),
    description: "Free Entertainment. Everywhere.",
    potentialAction: {
      "@type": "SearchAction",
      target: `${siteUrl()}/search?q={query}`,
      "query-input": "required name=query",
    },
  };
  return (
    <main>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      {hero ? (
        <section className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-stone-950">
          <div className="absolute inset-0 opacity-50">
            <Poster movie={hero} priority />
          </div>
          <div className="relative bg-gradient-to-r from-black via-black/80 to-black/20 px-6 py-16 sm:px-10">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber">Featured</p>
            <h1 className="mt-3 max-w-xl font-display text-5xl leading-none sm:text-6xl">{hero.title}</h1>
            <p className="mt-4 max-w-xl text-sm text-ink/80 sm:text-base">{hero.description}</p>
            <p className="mt-3 text-sm text-ink/70">
              {hero.genres[0]} · {hero.releaseYear} · {hero.country} · {hero.ageRating} · {formatRuntime(hero.runtimeSeconds)}
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              {watch ? (
                <Link href={`/watch/${hero.slug}`} data-testid="watch-now" className="rounded-full bg-amber px-5 py-3 text-sm font-semibold text-stone-950">
                  Watch now
                </Link>
              ) : null}
              <Link href={`/movies/${hero.slug}`} className="rounded-full border border-white/20 px-5 py-3 text-sm">
                Details
              </Link>
            </div>
          </div>
        </section>
      ) : null}
      <ContinueRow />
      <MovieRow title="Trending" movies={pick(catalog.movies, catalog.trending)} href="/movies" />
      <MovieRow title="Recently added" movies={[...catalog.movies].filter((movie) => movie.published).sort((a, b) => b.createdAt.localeCompare(a.createdAt)).slice(0, 10)} href="/movies" />
      <MovieRow title="Popular" movies={pick(catalog.movies, catalog.popular)} href="/movies" />
      <MovieRow title="Kids Movies" href="/kids" movies={catalog.movies.filter(isApprovedForKids)} />
      <MovieRow title="African Cinema" href="/categories/african-cinema" movies={moviesInCategory(catalog.movies, "african-cinema")} empty="No verified African title is in the catalogue yet." />
      <MovieRow title="Animated" href="/categories/animated-movies" movies={moviesInCategory(catalog.movies, "animated-movies")} />
      <MovieRow title="Family" href="/categories/family-entertainment" movies={moviesInCategory(catalog.movies, "family-entertainment")} />
      <MovieRow title="Documentaries" href="/categories/documentaries" movies={moviesInCategory(catalog.movies, "documentaries")} />
      <MovieRow title="Classic" href="/categories/classic-cinema" movies={moviesInCategory(catalog.movies, "classic-cinema").slice(0, 12)} />
      <MovieRow title="Educational" href="/categories/educational-movies" movies={moviesInCategory(catalog.movies, "educational-movies")} />
    </main>
  );
}
