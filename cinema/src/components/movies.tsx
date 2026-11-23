"use client";

import Image from "next/image";
import Link from "next/link";
import { Heart, Play } from "lucide-react";
import { useEffect, useState } from "react";
import { canWatch } from "@/lib/catalog";
import { browserLibrary } from "@/lib/local-library";
import type { Movie } from "@/lib/types";
import { formatRuntime } from "@/lib/utils";
import { useI18n } from "./i18n-provider";
import { Badge } from "./ui";

export function Poster({ movie, priority = false }: { movie: Pick<Movie, "title" | "posterUrl">; priority?: boolean }) {
  if (!movie.posterUrl) {
    return (
      <div className="poster-fallback flex h-full w-full items-end p-3">
        <span className="font-display text-lg leading-tight">{movie.title}</span>
      </div>
    );
  }
  return (
    <Image
      src={movie.posterUrl}
      alt=""
      fill
      priority={priority}
      sizes="(max-width: 768px) 46vw, 200px"
      className="object-cover"
    />
  );
}

export function MovieCard({ movie, kids = false }: { movie: Movie; kids?: boolean }) {
  const { t } = useI18n();
  const watch = canWatch(movie);
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    setSaved(browserLibrary().read().favourites.includes(movie.slug));
  }, [movie.slug]);

  return (
    <article className={`group relative w-[168px] shrink-0 sm:w-[196px] ${kids ? "text-stone-900" : ""}`}>
      <Link href={`/movies/${movie.slug}`} className="block">
        <div className="relative aspect-[2/3] overflow-hidden rounded-2xl bg-stone-900 shadow-lift">
          <Poster movie={movie} />
          <div className="absolute inset-x-0 bottom-0 flex items-center justify-between bg-gradient-to-t from-black/80 to-transparent p-2">
            <Badge className={kids ? "border-stone-900/20 bg-white/90 text-stone-900" : ""}>{movie.ageRating}</Badge>
            {watch ? <Play className="h-4 w-4 text-amber" aria-hidden /> : null}
          </div>
        </div>
        <h3 className="mt-2 line-clamp-2 font-display text-base leading-snug">{movie.title}</h3>
        <p className={`text-xs ${kids ? "text-stone-700" : "text-ink/60"}`}>
          {movie.releaseYear} · {movie.country} · {formatRuntime(movie.runtimeSeconds)}
        </p>
      </Link>
      <button
        type="button"
        aria-pressed={saved}
        aria-label={saved ? `Remove ${movie.title} from favourites` : `Save ${movie.title} on this device`}
        className="absolute right-2 top-2 rounded-full bg-black/60 p-1.5 text-white"
        onClick={() => {
          const next = browserLibrary().toggleFavourite(movie.slug);
          setSaved(next.favourites.includes(movie.slug));
        }}
      >
        <Heart className={`h-4 w-4 ${saved ? "fill-coral text-coral" : ""}`} />
      </button>
      <span className="sr-only">{watch ? t("cta.watch") : "No authorized player"}</span>
    </article>
  );
}

export function MovieRow({
  title,
  href,
  movies,
  kids = false,
  empty,
}: {
  title: string;
  href?: string;
  movies: Movie[];
  kids?: boolean;
  empty?: string;
}) {
  return (
    <section className="mt-8">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="font-display text-2xl">{title}</h2>
        {href ? (
          <Link href={href} className="text-sm text-amber">
            See all
          </Link>
        ) : null}
      </div>
      {movies.length === 0 ? (
        <p className={`rounded-2xl border border-dashed px-4 py-6 text-sm ${kids ? "border-stone-400" : "border-white/20 text-ink/70"}`}>
          {empty}
        </p>
      ) : (
        <div className="row-scroll">{movies.map((movie) => <MovieCard key={movie.slug} movie={movie} kids={kids} />)}</div>
      )}
    </section>
  );
}
