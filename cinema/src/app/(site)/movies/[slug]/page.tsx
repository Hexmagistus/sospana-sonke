import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { FavouriteToggle } from "@/components/favourite-toggle";
import { MovieCard, Poster } from "@/components/movies";
import { canWatch, movieBySlug, preferredSource } from "@/lib/catalog";
import { similarMovies } from "@/lib/recommendations";
import { getPublicCatalog } from "@/lib/public-catalog";
import { formatRuntime, isoDuration, siteUrl } from "@/lib/utils";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const catalog = await getPublicCatalog();
  const movie = movieBySlug(catalog.movies, slug);
  if (!movie) return { title: "Title" };
  return {
    title: movie.title,
    description: movie.description,
    alternates: { canonical: `/movies/${movie.slug}` },
    openGraph: { images: movie.posterUrl ? [movie.posterUrl] : [] },
  };
}

export default async function MoviePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const catalog = await getPublicCatalog();
  const movie = movieBySlug(catalog.movies, slug);
  if (!movie || !movie.published) notFound();
  const source = preferredSource(movie);
  const watch = canWatch(movie);
  const provider = catalog.sources.find((item) => item.id === source?.providerId);
  const similar = similarMovies(movie, catalog.movies);
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": movie.contentType === "documentary" ? "Movie" : "Movie",
    name: movie.title,
    description: movie.description,
    image: movie.posterUrl,
    datePublished: String(movie.releaseYear),
    duration: isoDuration(movie.runtimeSeconds),
    countryOfOrigin: movie.country,
    inLanguage: movie.language,
    director: { "@type": "Person", name: movie.director },
    actor: movie.cast.map((name) => ({ "@type": "Person", name })),
    isAccessibleForFree: watch,
    ...(watch ? { potentialAction: { "@type": "WatchAction", target: `${siteUrl()}/watch/${movie.slug}` } } : {}),
  };
  return (
    <main>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <div className="grid gap-8 md:grid-cols-[220px_1fr]">
        <div className="relative aspect-[2/3] overflow-hidden rounded-3xl bg-stone-900">
          <Poster movie={movie} priority />
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-amber">{movie.country}</p>
          <h1 className="mt-2 font-display text-4xl sm:text-5xl">{movie.title}</h1>
          <p className="mt-4 max-w-2xl text-ink/80">{movie.description}</p>
          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
            <Fact label="Year" value={String(movie.releaseYear)} />
            <Fact label="Runtime" value={formatRuntime(movie.runtimeSeconds)} />
            <Fact label="Language" value={movie.language} />
            <Fact label="Director" value={movie.director || "Not stated"} />
            <Fact label="Age rating" value={movie.ageRating} />
            <Fact label="Type" value={movie.contentType} />
          </dl>
          {movie.cast.length > 0 ? <p className="mt-3 text-sm text-ink/70">Cast: {movie.cast.join(", ")}</p> : null}
          <p className="mt-2 text-sm text-ink/70">Genres: {movie.genres.join(", ")}</p>
          <div className="mt-6 flex flex-wrap gap-3">
            <FavouriteToggle slug={movie.slug} title={movie.title} />
            {watch && source ? (
              <Link href={`/watch/${movie.slug}`} data-testid="watch-now" className="rounded-full bg-amber px-5 py-3 text-sm font-semibold text-stone-950">
                Watch now
              </Link>
            ) : (
              <p className="rounded-2xl border border-white/15 px-4 py-3 text-sm" data-testid="no-playback">
                No authorized player is on file for this title.
              </p>
            )}
          </div>
          {movie.trailerUrl ? (
            <p className="mt-4 text-sm">
              Trailer: <a href={movie.trailerUrl}>{movie.trailerUrl}</a>
            </p>
          ) : (
            <p className="mt-4 text-sm text-ink/60">No separate trailer is on file.</p>
          )}
        </div>
      </div>
      <section className="mt-10 rounded-3xl border border-white/10 bg-white/5 p-5">
        <h2 className="font-display text-2xl">Rights</h2>
        {source ? (
          <div className="mt-3 space-y-2 text-sm text-ink/80">
            <p>Licence: {source.licenceType}. Territories on the source record: {source.licenceTerritories.join(", ")}.</p>
            <p>
              Evidence:{" "}
              <a className="text-amber" href={source.licenceEvidenceUrl}>
                {source.licenceEvidenceUrl}
              </a>
            </p>
            <p>
              Source record:{" "}
              <a className="text-amber" href={source.sourceRecordUrl}>
                {source.sourceRecordUrl}
              </a>
            </p>
            <p>Rights holder: {source.rightsHolder}. Playback host: {provider?.providerName ?? "the source on the record"}.</p>
            <p>Last checked: {source.lastVerifiedAt}. Status: {source.playbackStatus}.</p>
            <p>{source.qualityNote}</p>
            {movie.note ? <p>{movie.note}</p> : null}
            <p>Public-domain status can differ by country. This page is not a promise that every territory treats the work the same way.</p>
          </div>
        ) : (
          <p className="mt-3 text-sm">There is no verified playback source. Look for an official edition from the rights holder.</p>
        )}
        {movie.review ? (
          <p className="mt-3 text-sm text-ink/70">
            Kids review: {movie.review.reviewStatus} ({movie.review.ageSuitability}). {movie.review.reviewNotes}
          </p>
        ) : null}
      </section>
      <section className="mt-10">
        <h2 className="font-display text-2xl">Similar titles</h2>
        <div className="mt-4 flex flex-wrap gap-4">
          {similar.map((item) => (
            <MovieCard key={item.slug} movie={item} />
          ))}
        </div>
      </section>
    </main>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-ink/50">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
