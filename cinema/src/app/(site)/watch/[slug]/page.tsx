import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Player } from "@/components/player";
import { MovieCard } from "@/components/movies";
import { canWatch, isApprovedForKids, movieBySlug, preferredSource } from "@/lib/catalog";
import { similarMovies } from "@/lib/recommendations";
import { getPublicCatalog } from "@/lib/public-catalog";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const catalog = await getPublicCatalog();
  const movie = movieBySlug(catalog.movies, slug);
  return { title: movie ? `Watch ${movie.title}` : "Watch", robots: { index: false, follow: true } };
}

export default async function WatchPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const catalog = await getPublicCatalog();
  const movie = movieBySlug(catalog.movies, slug);
  if (!movie || !movie.published) notFound();
  const source = preferredSource(movie);
  const similar = similarMovies(movie, catalog.movies, 6);
  return (
    <main>
      <p className="text-sm text-ink/60">
        <Link href={`/movies/${movie.slug}`} className="text-amber">
          {movie.title}
        </Link>
      </p>
      <h1 className="mt-2 font-display text-4xl">Watch {movie.title}</h1>
      {source && canWatch(movie) ? (
        <div className="mt-6">
          <Player movie={movie} source={source} countries={catalog.movies.map((item) => item.country)} />
          <p className="mt-4 text-xs text-ink/50">
            Age rating {movie.ageRating}. Playback does not start by itself.
            {isApprovedForKids(movie) ? " This title was approved for Kids Cinema." : " This title is not in Kids Cinema."}
          </p>
        </div>
      ) : (
        <p className="mt-6 rounded-2xl border border-white/15 p-4 text-sm" data-testid="no-playback">
          Watch now is hidden because no authorized player is on file. The detail page lists what we do know.
        </p>
      )}
      {source?.subtitles.length ? (
        <ul className="mt-4 text-sm">
          {source.subtitles.map((track) => (
            <li key={track.url}>
              <a className="text-amber" href={track.url}>
                {track.label}
              </a>
            </li>
          ))}
        </ul>
      ) : null}
      <section className="mt-10">
        <h2 className="font-display text-2xl">More from the catalogue</h2>
        <div className="mt-4 flex flex-wrap gap-4">
          {similar.map((item) => (
            <MovieCard key={item.slug} movie={item} kids={isApprovedForKids(movie)} />
          ))}
        </div>
      </section>
    </main>
  );
}
