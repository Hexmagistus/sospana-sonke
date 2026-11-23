import raw from "../../data/catalog.json";
import type { CatalogFile, Movie, StreamSource } from "./types";

const file = raw as CatalogFile;

export function seedCatalog(): CatalogFile {
  return file;
}

export function publishedMovies(movies: readonly Movie[]): Movie[] {
  return movies.filter((movie) => movie.published);
}

export function preferredSource(movie: Movie): StreamSource | null {
  const ready = movie.sources.filter(
    (source) =>
      source.rightsVerified &&
      source.playbackStatus === "available" &&
      source.licenceEvidenceUrl.startsWith("http") &&
      source.url.startsWith("https://"),
  );
  return (
    ready.find((source) => source.playbackType === "mp4") ??
    ready.find((source) => source.playbackType === "hls") ??
    ready.find((source) => source.playbackType === "embed") ??
    null
  );
}

export function canWatch(movie: Movie): boolean {
  return movie.published && preferredSource(movie) !== null;
}

export function movieBySlug(movies: readonly Movie[], slug: string): Movie | undefined {
  return movies.find((movie) => movie.slug === slug);
}

export const KIDS_GROUPS = [
  "preschool",
  "6-8",
  "9-12",
  "family",
] as const;

export type KidsGroup = (typeof KIDS_GROUPS)[number];

export function isApprovedForKids(movie: Movie): boolean {
  if (!movie.published || !movie.review || movie.review.reviewStatus !== "approved") return false;
  if (!KIDS_GROUPS.includes(movie.review.ageSuitability as KidsGroup)) return false;
  return canWatch(movie);
}

const GATED_CATEGORIES = new Set(["kids-movies", "cartoons", "family-entertainment"]);

export function categoryIsKidsGated(slug: string): boolean {
  return slug.startsWith("kids-") || GATED_CATEGORIES.has(slug);
}

export function moviesInCategory(movies: readonly Movie[], slug: string): Movie[] {
  const matched = publishedMovies(movies).filter((movie) => movie.categorySlugs.includes(slug));
  if (!categoryIsKidsGated(slug)) return matched;
  return matched.filter(isApprovedForKids);
}

export function kidsByGroup(movies: readonly Movie[], group: KidsGroup): Movie[] {
  return publishedMovies(movies).filter(
    (movie) => isApprovedForKids(movie) && movie.review?.ageSuitability === group,
  );
}
