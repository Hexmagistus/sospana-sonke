import { describe, expect, it } from "vitest";
import { canWatch, isApprovedForKids, kidsByGroup, moviesInCategory, preferredSource, seedCatalog } from "./catalog";

const catalog = seedCatalog();

describe("demonstration catalogue", () => {
  it("only lists titles with a licence and an archive playback URL", () => {
    expect(catalog.movies.length).toBeGreaterThan(20);
    for (const movie of catalog.movies) {
      expect(movie.sources.length).toBeGreaterThan(0);
      for (const source of movie.sources) {
        expect(source.rightsVerified).toBe(true);
        expect(source.licenceEvidenceUrl).toMatch(/^https?:\/\//);
        expect(source.url).toMatch(/^https:\/\/archive\.org\//);
        expect(source.playbackStatus).toBe("available");
      }
      expect(canWatch(movie)).toBe(true);
      expect(preferredSource(movie)?.url.startsWith("https://")).toBe(true);
    }
  });

  it("keeps unapproved animation out of Kids Cinema", () => {
    const sintel = catalog.movies.find((movie) => movie.slug === "sintel");
    const bunny = catalog.movies.find((movie) => movie.slug === "big-buck-bunny");
    const llama = catalog.movies.find((movie) => movie.slug === "caminandes-llama-drama");
    expect(sintel?.review?.reviewStatus).toBe("rejected");
    expect(isApprovedForKids(sintel!)).toBe(false);
    expect(isApprovedForKids(bunny!)).toBe(true);
    expect(kidsByGroup(catalog.movies, "preschool").map((movie) => movie.slug)).toContain("caminandes-llama-drama");
    expect(kidsByGroup(catalog.movies, "preschool").map((movie) => movie.slug)).not.toContain("sintel");
    expect(kidsByGroup(catalog.movies, "preschool").map((movie) => movie.slug)).not.toContain("big-buck-bunny");
    expect(moviesInCategory(catalog.movies, "animated-movies").some((movie) => movie.slug === "sintel")).toBe(true);
    expect(moviesInCategory(catalog.movies, "kids-movies").some((movie) => movie.slug === "sintel")).toBe(false);
    expect(isApprovedForKids(llama!)).toBe(true);
  });

  it("does not invent a South African or series title", () => {
    expect(moviesInCategory(catalog.movies, "south-african-movies")).toEqual([]);
    expect(moviesInCategory(catalog.movies, "african-cinema")).toEqual([]);
    expect(moviesInCategory(catalog.movies, "tv-series")).toEqual([]);
    expect(catalog.heroSlug).toBe("sherlock-jr");
  });
});
