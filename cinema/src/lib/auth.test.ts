import { describe, expect, it } from "vitest";
import { passwordsMatch, readSession, signSession } from "./auth";
import { archiveCandidate } from "./licence";
import { createLibrary } from "./local-library";
import { rateLimit, resetRateLimits } from "./rate-limit";

describe("admin session and local data", () => {
  it("accepts the configured password and rejects another", () => {
    expect(passwordsMatch("demo-cinema-change-me", "demo-cinema-change-me")).toBe(true);
    expect(passwordsMatch("wrong-password", "demo-cinema-change-me")).toBe(false);
  });

  it("signs and expires a session", () => {
    const token = signSession("admin@example.com", "secret", -10);
    expect(readSession(token, "secret")).toBeNull();
    const live = signSession("admin@example.com", "secret", 60);
    expect(readSession(live, "secret")?.email).toBe("admin@example.com");
    expect(readSession(live, "other-secret")).toBeNull();
  });

  it("stores favourites and can clear them", () => {
    const memory = new Map<string, string>();
    const library = createLibrary({
      getItem: (key) => memory.get(key) ?? null,
      setItem: (key, value) => void memory.set(key, value),
      removeItem: (key) => void memory.delete(key),
    });
    library.toggleFavourite("sherlock-jr");
    library.saveProgress({ slug: "sherlock-jr", title: "Sherlock Jr.", position: 12, duration: 100, updatedAt: "2026-11-23T00:00:00Z", player: "mp4" });
    expect(library.read().favourites).toEqual(["sherlock-jr"]);
    expect(library.read().progress[0]?.position).toBe(12);
    library.clear();
    expect(library.read().favourites).toEqual([]);
  });

  it("rate limits and refuses a non-commercial discovery item", () => {
    resetRateLimits();
    expect(rateLimit("k", 1, 1000, 0).ok).toBe(true);
    expect(rateLimit("k", 1, 1000, 10).ok).toBe(false);
    expect(archiveCandidate({ identifier: "x", title: "X", licenseurl: "https://creativecommons.org/licenses/by-nc/4.0/" })).toBeNull();
  });
});
