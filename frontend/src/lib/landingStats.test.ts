import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { COUNTRY_FLAGS } from "./countryFlags";
import { compareCountries } from "./directoryFilters";
import {
  countryRows, parseStats, readCachedStats, snapshotDirectoryDescription, snapshotStats, writeCachedStats,
} from "./landingStats";
import { coverageText, tierOf, tierTotals, TIERS } from "./regions";

const live = {
  employers: 5001,
  by_country: { "South Africa": 996 },
  with_link: 2700,
  by_country_with_link: { "South Africa": 730, Canada: 11, "United States": 30, Singapore: 9, Africa: 3 },
};

describe("landing stats", () => {
  it("snapshot adds up and has no placeholder numbers", () => {
    const snap = snapshotStats();
    const sum = Object.values(snap.byCountry).reduce((a, b) => a + b, 0);
    assert.equal(sum, snap.total);
    assert.equal(snap.source, "snapshot");
    // Ceiling stays under the all-rows employer count (5,800 on 2026-10-07),
    // so a payload that also counts employers with no careers link still fails.
    assert.ok(snap.total > 3000 && snap.total < 5000, `snapshot total ${snap.total}`);
  });

  it("directory metadata uses the snapshot, not an old Africa-only count", () => {
    const text = snapshotDirectoryDescription();
    assert.match(text, /3,439 employers/);
    assert.match(text, /South America/);
    assert.match(text, /7 October 2026/);
    assert.doesNotMatch(text, /2,400/);
    assert.doesNotMatch(text, /26 African/);
  });

  it("every snapshot country has a flag and a region (nothing falls into Africa by default)", () => {
    for (const name of Object.keys(snapshotStats().byCountry)) {
      if (name === "International") continue;
      assert.ok(COUNTRY_FLAGS[name], `no flag for ${name}`);
      assert.notEqual(tierOf(name), "other", `${name} has no region`);
    }
  });

  it("uses the direct-link counts and refuses an older payload without them", () => {
    const parsed = parseStats(live);
    assert.equal(parsed?.total, 2700);
    assert.equal(parsed?.source, "live");
    assert.equal(parseStats({ employers: 5001, by_country: { "South Africa": 996 } }), null);
    assert.equal(parseStats({ with_link: 0, by_country_with_link: { A: 1 } }), null);
    assert.equal(parseStats({ with_link: 10, by_country_with_link: [] }), null);
    assert.equal(parseStats(null), null);
    assert.equal(parseStats("x"), null);
    const odd = parseStats({ with_link: 5, by_country_with_link: { A: 2, B: "7", C: -1, D: 0 } });
    assert.deepEqual(odd?.byCountry, { A: 2 });
  });

  it("keeps the last live answer in the browser for a week", () => {
    const store = new Map<string, string>();
    const storage = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => void store.set(k, v) };
    const t0 = 1_000_000;
    writeCachedStats(storage, { employers: 1 }, t0);
    assert.equal(store.size, 0, "an old-shape payload is not cached");
    writeCachedStats(storage, live, t0);
    assert.equal(readCachedStats(storage, t0 + 1000)?.source, "cached");
    assert.equal(readCachedStats(storage, t0 + 1000)?.total, 2700);
    assert.equal(readCachedStats(storage, t0 + 8 * 24 * 3600 * 1000), null);
    assert.equal(readCachedStats(storage, t0 - 5), null);
    assert.equal(readCachedStats({ getItem: () => "{not json" }, t0), null);
    assert.equal(readCachedStats(undefined, t0), null);
  });

  it("lists real countries only, biggest first", () => {
    const rows = countryRows(live.by_country_with_link);
    assert.deepEqual(rows.map((r) => r.name), ["South Africa", "United States", "Canada", "Singapore"]);
    assert.ok(rows.every((r) => r.flag));
  });
});

describe("regions", () => {
  it("names North America and Asia once they have employers, in the standing order", () => {
    const snap = countryRows(snapshotStats().byCountry);
    assert.equal(coverageText(snap), "Africa, Oceania, Europe, South America, North America and Asia");
    assert.equal(coverageText([{ name: "South Africa", count: 5 }]), "Africa");
    assert.equal(
      coverageText([{ name: "South Africa", count: 5 }, { name: "Canada", count: 1 }]),
      "Africa and North America",
    );
  });

  it("tier order matches the standing country order", () => {
    assert.deepEqual(TIERS.slice(0, 3).map((t) => t.id), ["south-africa", "sadc", "africa"]);
    assert.ok(compareCountries("South Africa", "Botswana") < 0);
    assert.ok(compareCountries("Botswana", "Kenya") < 0);
    assert.ok(compareCountries("Kenya", "Canada") < 0);
    assert.equal(tierOf("Botswana"), "sadc");
    assert.equal(tierOf("Kenya"), "africa");
    assert.equal(tierOf("Hong Kong"), "asia");
    assert.equal(tierOf("Monaco"), "europe");
    assert.equal(tierOf("San Marino"), "europe");
    assert.equal(tierOf("North Macedonia"), "europe");
    assert.equal(tierOf("Myanmar"), "asia");
    assert.equal(tierOf("Tajikistan"), "asia");
    assert.equal(tierOf("Turkmenistan"), "asia");
    assert.equal(tierOf("Atlantis"), "other");
  });

  it("totals real countries per tier and skips buckets", () => {
    const totals = tierTotals(countryRows({ ...live.by_country_with_link, International: 4 }));
    assert.equal(totals["north-america"].countries, 2);
    assert.equal(totals["north-america"].employers, 41);
    assert.equal(totals.asia.employers, 9);
    assert.equal(totals.africa.countries, 0);
  });
});
