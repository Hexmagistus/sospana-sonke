import { canWatch, isApprovedForKids } from "./catalog";
import type { Movie } from "./types";

export type SearchSort = "relevance" | "title" | "year" | "runtime" | "newest";

export type SearchQuery = {
  q?: string;
  country?: string;
  language?: string;
  genre?: string;
  category?: string;
  contentType?: string;
  yearFrom?: number;
  yearTo?: number;
  playbackOnly?: boolean;
  kidsOnly?: boolean;
  sort?: SearchSort;
};

export type SearchHit = {
  movie: Movie;
  score: number;
};

function normalize(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function tokens(value: string): string[] {
  return normalize(value).split(" ").filter((token) => token.length > 1 || /\d/.test(token));
}

export function levenshtein(left: string, right: string): number {
  if (left === right) return 0;
  if (Math.abs(left.length - right.length) > 2) return 9;
  const previous = Array.from({ length: left.length + 1 }, (_, index) => index);
  for (let i = 1; i <= right.length; i += 1) {
    let diagonal = previous[0];
    previous[0] = i;
    for (let j = 1; j <= left.length; j += 1) {
      const stored = previous[j];
      const cost = left[j - 1] === right[i - 1] ? 0 : 1;
      previous[j] = Math.min(previous[j] + 1, previous[j - 1] + 1, diagonal + cost);
      diagonal = stored;
    }
  }
  return previous[left.length];
}

function fuzzyLimit(word: string): number {
  if (word.length >= 8) return 2;
  if (word.length >= 5) return 1;
  return 0;
}

function fieldScore(queryTokens: string[], words: string[], exactWeight: number, fuzzyWeight: number): number {
  if (words.length === 0) return 0;
  let score = 0;
  for (const query of queryTokens) {
    if (words.includes(query)) {
      score += exactWeight;
      continue;
    }
    const limit = fuzzyLimit(query);
    if (!limit) continue;
    const distance = Math.min(...words.map((word) => levenshtein(query, word)));
    if (distance <= limit) score += fuzzyWeight;
  }
  return score;
}

export function searchMovies(movies: readonly Movie[], query: SearchQuery): { hits: SearchHit[]; corrected: string | null } {
  const q = (query.q ?? "").trim();
  const queryTokens = tokens(q);
  const hits: SearchHit[] = [];

  for (const movie of movies) {
    if (!movie.published) continue;
    if (query.country && movie.country !== query.country) continue;
    if (query.language && movie.language !== query.language) continue;
    if (query.genre && !movie.genres.some((genre) => genre.toLowerCase() === query.genre?.toLowerCase())) continue;
    if (query.category && !movie.categorySlugs.includes(query.category)) continue;
    if (query.contentType && movie.contentType !== query.contentType) continue;
    if (query.yearFrom && movie.releaseYear < query.yearFrom) continue;
    if (query.yearTo && movie.releaseYear > query.yearTo) continue;
    if (query.playbackOnly && !canWatch(movie)) continue;
    if (query.kidsOnly && !isApprovedForKids(movie)) continue;

    if (queryTokens.length === 0) {
      hits.push({ movie, score: 1 });
      continue;
    }

    const titleWords = tokens(movie.title);
    const people = tokens(`${movie.director} ${movie.cast.join(" ")}`);
    const other = tokens(
      `${movie.genres.join(" ")} ${movie.country} ${movie.language} ${movie.description} ${movie.releaseYear}`,
    );
    const score =
      fieldScore(queryTokens, titleWords, 50, 28) +
      fieldScore(queryTokens, people, 24, 12) +
      fieldScore(queryTokens, other, 10, 4);
    if (score > 0) hits.push({ movie, score });
  }

  const sort = query.sort ?? (q ? "relevance" : "newest");
  hits.sort((a, b) => compareHits(a, b, sort));

  let corrected: string | null = null;
  if (q && hits.length > 0) {
    const exact = hits.some((hit) => normalize(hit.movie.title).includes(normalize(q)) || tokens(hit.movie.title).some((word) => queryTokens.includes(word)));
    if (!exact) corrected = hits[0].movie.title;
  }

  return { hits, corrected };
}

function compareHits(a: SearchHit, b: SearchHit, sort: SearchSort): number {
  if (sort === "title") return a.movie.title.localeCompare(b.movie.title) || b.score - a.score;
  if (sort === "year") return b.movie.releaseYear - a.movie.releaseYear || b.score - a.score;
  if (sort === "runtime") return a.movie.runtimeSeconds - b.movie.runtimeSeconds || a.movie.title.localeCompare(b.movie.title);
  if (sort === "newest") return b.movie.createdAt.localeCompare(a.movie.createdAt) || a.movie.title.localeCompare(b.movie.title);
  return b.score - a.score || a.movie.title.localeCompare(b.movie.title);
}

export function suggestTitles(movies: readonly Movie[], q: string, limit = 6): string[] {
  const { hits } = searchMovies(movies, { q, sort: "relevance" });
  return hits.slice(0, limit).map((hit) => hit.movie.title);
}
