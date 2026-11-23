import { describe, expect, it } from "vitest";
import { seedCatalog } from "./catalog";
import { similarMovies } from "./recommendations";

describe("recommendations", () => {
  it("does not recommend a rejected film from a kids title", () => {
    const movies = seedCatalog().movies;
    const llama = movies.find((movie) => movie.slug === "caminandes-llama-drama")!;
    const similar = similarMovies(llama, movies);
    expect(similar.map((movie) => movie.slug)).not.toContain("sintel");
    expect(similar.every((movie) => movie.review?.reviewStatus === "approved")).toBe(true);
  });
});
