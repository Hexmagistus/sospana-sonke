import { describe, expect, it } from "vitest";
import { seedCatalog } from "./catalog";
import { levenshtein, searchMovies } from "./search";

const movies = seedCatalog().movies;

describe("search", () => {
  it("finds a title with a small typo", () => {
    expect(levenshtein("sherlok", "sherlock")).toBe(1);
    const result = searchMovies(movies, { q: "sherlok" });
    expect(result.hits.slice(0, 10).map((hit) => hit.movie.slug)).toContain("sherlock-jr");
    expect(result.corrected?.toLowerCase()).toContain("sherlock");
  });

  it("filters by country, South African titles included", () => {
    const german = searchMovies(movies, { country: "Germany" });
    expect(german.hits.every((hit) => hit.movie.country === "Germany")).toBe(true);
    expect(german.hits.map((hit) => hit.movie.slug)).toContain("nosferatu");
    const southAfrica = searchMovies(movies, { country: "South Africa" });
    expect(southAfrica.hits.length).toBeGreaterThan(0);
    expect(southAfrica.hits.every((hit) => hit.movie.country === "South Africa")).toBe(true);
  });

  it("finds a person and a kids-only shelf", () => {
    const price = searchMovies(movies, { q: "Vincent Price" });
    expect(price.hits.map((hit) => hit.movie.slug)).toEqual(expect.arrayContaining(["house-on-haunted-hill", "the-last-man-on-earth"]));
    const kids = searchMovies(movies, { kidsOnly: true });
    expect(kids.hits.every((hit) => hit.movie.review?.reviewStatus === "approved")).toBe(true);
    expect(kids.hits.map((hit) => hit.movie.slug)).not.toContain("sintel");
  });
});
