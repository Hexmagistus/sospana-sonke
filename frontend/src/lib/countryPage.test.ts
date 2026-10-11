import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it } from "node:test";
import { countryFromSlug, countrySlug, suggestCountries } from "./countryPage.js";

describe("country page slugs", () => {
  it("folds accents and punctuation into one hyphenated slug", () => {
    assert.equal(countrySlug("Côte d'Ivoire"), "cote-d-ivoire");
    assert.equal(countrySlug("Sao Tome and Principe"), "sao-tome-and-principe");
    assert.equal(countrySlug("South Africa"), "south-africa");
    assert.equal(countrySlug("DR Congo"), "dr-congo");
  });

  it("returns a name only when exactly one country uses that slug", () => {
    const names = ["South Africa", "Côte d'Ivoire", "Ivory Coast"];
    assert.equal(countryFromSlug("south-africa", names), "South Africa");
    assert.equal(countryFromSlug("missing", names), null);
    assert.equal(countryFromSlug("ivory-coast", ["Ivory Coast", "Ivory Coast"]), null);
  });

  it("suggests countries that start with the letters before the others", () => {
    const rows = [
      { name: "South Africa" },
      { name: "South Sudan" },
      { name: "Sudan" },
    ];
    assert.deepEqual(
      suggestCountries("su", rows).map((row) => row.name),
      ["Sudan", "South Sudan"],
    );
    assert.deepEqual(suggestCountries("", rows), []);
  });

  it("gives every snapshot country its own slug", () => {
    const snapshot = JSON.parse(readFileSync(
      resolve(process.cwd(), "src/data/directory-snapshot.json"),
      "utf8",
    )) as { by_country_with_link: Record<string, number> };
    const names = Object.entries(snapshot.by_country_with_link)
      .filter(([name, count]) => count > 0 && name !== "International" && name !== "Africa")
      .map(([name]) => name);
    const slugs = names.map(countrySlug);
    assert.equal(new Set(slugs).size, slugs.length);
    assert.equal(countryFromSlug("south-africa", names), "South Africa");
  });
});
