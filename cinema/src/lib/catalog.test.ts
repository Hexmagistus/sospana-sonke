import { describe, expect, it } from "vitest";
import { canWatch, isApprovedForKids, kidsByGroup, moviesInCategory, preferredSource, seedCatalog } from "./catalog";

const catalog = seedCatalog();

describe("demonstration catalogue", () => {
  it("only lists titles with a licence and an Internet Archive or official YouTube playback URL", () => {
    expect(catalog.movies.length).toBeGreaterThan(20);
    for (const movie of catalog.movies) {
      expect(movie.sources.length).toBeGreaterThan(0);
      for (const source of movie.sources) {
        expect(source.rightsVerified).toBe(true);
        expect(source.licenceEvidenceUrl).toMatch(/^https?:\/\//);
        expect(source.url).toMatch(/^https:\/\/(archive\.org\/|www\.youtube-nocookie\.com\/embed\/[A-Za-z0-9_-]{11}$)/);
        if (source.providerSlug === "youtube") {
          expect(source.playbackType).toBe("embed");
          expect(source.licenceEvidenceUrl).toMatch(/^https:\/\/(www\.youtube\.com\/channel\/UC|creativecommons\.org\/)/);
          expect(source.sourceRecordUrl).toMatch(/^https:\/\/www\.youtube\.com\/watch\?v=/);
        }
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

  it("fills the African, South African, series, anime and nature shelves only from verified sources", () => {
    for (const slug of ["south-african-movies", "african-cinema", "tv-series", "anime", "nature-and-wildlife"]) {
      expect(moviesInCategory(catalog.movies, slug).length).toBeGreaterThan(0);
    }
    for (const movie of moviesInCategory(catalog.movies, "south-african-movies")) {
      expect(movie.country).toBe("South Africa");
      expect(movie.sources.every((source) => source.rightsVerified && source.providerSlug === "youtube")).toBe(true);
    }
    expect(catalog.heroSlug).toBe("sherlock-jr");
  });

  it("keeps pending kids candidates out of every Kids Cinema shelf", () => {
    const pending = catalog.movies.filter((movie) => movie.review?.reviewStatus === "pending");
    expect(pending.length).toBeGreaterThan(0);
    const kidsSlugs = new Set(
      (["preschool", "6-8", "9-12", "family"] as const).flatMap((group) => kidsByGroup(catalog.movies, group).map((movie) => movie.slug)),
    );
    for (const movie of pending) {
      expect(isApprovedForKids(movie)).toBe(false);
      expect(kidsSlugs.has(movie.slug)).toBe(false);
      expect(movie.categorySlugs.some((slug) => slug.startsWith("kids-") || slug === "cartoons" || slug === "family-entertainment")).toBe(false);
    }
  });

  it("respects region limits a rights holder sets", () => {
    const gundam = catalog.movies.find((movie) => movie.slug === "mobile-suit-gundam-i");
    expect(gundam).toBeDefined();
    expect(gundam!.sources[0].licenceTerritories).toContain("South Africa");
    expect(gundam!.sources[0].licenceTerritories).not.toContain("WORLD");
  });
});
