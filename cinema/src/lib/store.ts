import "server-only";

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { seedCatalog } from "./catalog";
import type { CatalogFile, Movie, Review, Takedown } from "./types";

function asReview(value: Review | null | undefined): Review | null {
  return value ?? null;
}

export type Overlay = {
  movies: Record<string, Movie>;
  hidden: string[];
  takedowns: Takedown[];
  reviews: Record<string, Review>;
};

const empty = (): Overlay => ({ movies: {}, hidden: [], takedowns: [], reviews: {} });

export function overlayPath(): string {
  return path.join(process.cwd(), "data", "runtime-state.json");
}

export function readOverlay(file = overlayPath()): Overlay {
  try {
    const parsed = JSON.parse(readFileSync(file, "utf8")) as Partial<Overlay>;
    return {
      movies: parsed.movies ?? {},
      hidden: parsed.hidden ?? [],
      takedowns: parsed.takedowns ?? [],
      reviews: parsed.reviews ?? {},
    };
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === "ENOENT") return empty();
    throw new Error(`Could not read the demonstration store at ${file}: ${(error as Error).message}`);
  }
}

export function writeOverlay(overlay: Overlay, file = overlayPath()): void {
  mkdirSync(path.dirname(file), { recursive: true });
  writeFileSync(file, JSON.stringify(overlay, null, 2));
}

export function mergeCatalog(seed: CatalogFile = seedCatalog(), overlay: Overlay = readOverlay()): CatalogFile {
  const hidden = new Set(overlay.hidden);
  const movies: Movie[] = seed.movies
    .filter((movie) => !hidden.has(movie.slug))
    .map((movie) => {
      const replacement = overlay.movies[movie.slug];
      const review = asReview(overlay.reviews[movie.slug] ?? replacement?.review ?? movie.review);
      return replacement ? { ...replacement, review } : { ...movie, review };
    });
  for (const extra of Object.values(overlay.movies)) {
    if (!movies.some((movie) => movie.slug === extra.slug) && !hidden.has(extra.slug)) movies.push(extra);
  }
  return { ...seed, movies };
}

export function saveMovie(movie: Movie, file = overlayPath()): void {
  const overlay = readOverlay(file);
  overlay.movies[movie.slug] = movie;
  if (movie.review) overlay.reviews[movie.slug] = movie.review;
  writeOverlay(overlay, file);
}

export function saveReview(slug: string, review: Review, file = overlayPath()): void {
  const overlay = readOverlay(file);
  overlay.reviews[slug] = review;
  if (overlay.movies[slug]) overlay.movies[slug] = { ...overlay.movies[slug], review };
  writeOverlay(overlay, file);
}

export function saveTakedown(takedown: Takedown, file = overlayPath()): void {
  const overlay = readOverlay(file);
  overlay.takedowns = [takedown, ...overlay.takedowns.filter((item) => item.id !== takedown.id)];
  writeOverlay(overlay, file);
}

export function listTakedowns(file = overlayPath()): Takedown[] {
  return readOverlay(file).takedowns;
}
