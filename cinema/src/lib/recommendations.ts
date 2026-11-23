import { canWatch, isApprovedForKids } from "./catalog";
import type { Movie } from "./types";

export function similarMovies(movie: Movie, all: readonly Movie[], limit = 8): Movie[] {
  const kidsContext = isApprovedForKids(movie);
  const scored = all
    .filter((other) => other.slug !== movie.slug && other.published && canWatch(other))
    .filter((other) => (kidsContext ? isApprovedForKids(other) : true))
    .map((other) => {
      const sharedGenres = other.genres.filter((genre) => movie.genres.includes(genre)).length;
      let score = sharedGenres * 5;
      if (other.country === movie.country) score += 3;
      if (other.contentType === movie.contentType) score += 2;
      if (other.language === movie.language) score += 1;
      if (Math.abs(other.releaseYear - movie.releaseYear) <= 15) score += 1;
      if (isApprovedForKids(other) && kidsContext) score += 2;
      return { other, score };
    })
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || a.other.title.localeCompare(b.other.title));
  return scored.slice(0, limit).map((item) => item.other);
}
