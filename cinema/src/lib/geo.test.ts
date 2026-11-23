import { describe, expect, it } from "vitest";
import { playbackAllowed } from "./geo";

describe("playback regions", () => {
  it("allows a worldwide source in South Africa", () => {
    expect(playbackAllowed({ licenceTerritories: ["WORLD"] }, "South Africa").allowed).toBe(true);
  });

  it("blocks a country that is outside the source record", () => {
    const result = playbackAllowed({ licenceTerritories: ["United States"] }, "South Africa");
    expect(result.allowed).toBe(false);
    expect(result.reason).toContain("South Africa");
  });
});
