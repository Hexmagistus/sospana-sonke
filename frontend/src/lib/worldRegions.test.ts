import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, it } from "node:test";
import { groupOf } from "./countryExplorer";
import { BUCKET_CODES, KNOWN_COUNTRY_NAMES, countryCode, countryFlag } from "./countryCodes";
import { tierOf } from "./regions";
import { REGION_BY_CODE, WORLD_REGIONS, worldRegionOf } from "./worldRegions";

// Same canonical spellings as backend app/services/country_names.py.
const ALIASES: Record<string, string> = {
  "Ivory Coast": "Côte d'Ivoire", "Cape Verde": "Cabo Verde", "Republic of Congo": "Congo",
};

/** Country column of every seed CSV in the repo: the real directory data. */
function seedCountries(): string[] {
  const root = [join(process.cwd(), "..", "backend", "seed"), join(process.cwd(), "backend", "seed")].find((p) => {
    try { return statSync(p).isDirectory(); } catch { return false; }
  });
  if (!root) return [];
  const files: string[] = [];
  const walk = (dir: string) => {
    for (const f of readdirSync(dir)) {
      const full = join(dir, f);
      if (statSync(full).isDirectory()) walk(full);
      else if (f.endsWith(".csv")) files.push(full);
    }
  };
  walk(root);
  const out = new Set<string>();
  for (const file of files) {
    const text = readFileSync(file, "utf8").replace(/^\uFEFF/, "");
    const rows: string[][] = [];
    let row: string[] = [], cell = "", q = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (q) {
        if (c === '"' && text[i + 1] === '"') { cell += '"'; i++; }
        else if (c === '"') q = false;
        else cell += c;
      } else if (c === '"') q = true;
      else if (c === ",") { row.push(cell); cell = ""; }
      else if (c === "\n" || c === "\r") {
        if (c === "\r" && text[i + 1] === "\n") i++;
        row.push(cell); cell = "";
        if (row.length > 1 || row[0] !== "") rows.push(row);
        row = [];
      } else cell += c;
    }
    if (cell || row.length) { row.push(cell); rows.push(row); }
    const col = rows[0]?.indexOf("country") ?? -1;
    if (col < 0) continue;
    for (const r of rows.slice(1)) {
      const name = (r[col] ?? "").trim();
      if (name) out.add(ALIASES[name] ?? name);
    }
  }
  return Array.from(out);
}

const isBucket = (n: string) => n in BUCKET_CODES;

describe("world regions", () => {
  it("the seven regions come in the agreed order", () => {
    assert.deepEqual(WORLD_REGIONS.map((r) => r.label), [
      "Europe", "North America", "Central America & Caribbean", "South America", "Asia", "Middle East", "Oceania",
    ]);
  });

  it("every code is a real two-letter code in exactly one region", () => {
    for (const code of Object.keys(REGION_BY_CODE)) assert.match(code, /^[A-Z]{2}$/);
    assert.equal(worldRegionOf("ca"), "north-america");
    assert.equal(worldRegionOf(null), null);
  });

  it("no country the site knows by name lands in the Other fallback", () => {
    const stray = KNOWN_COUNTRY_NAMES.filter((n) => !isBucket(n) && groupOf(n) === "other");
    assert.deepEqual(stray, [], `unmapped countries: ${stray.join(", ")}`);
  });

  it("every directory country in the seed data is mapped to a group", () => {
    const names = seedCountries();
    assert.ok(names.length > 150, `expected the seed CSVs to list 150+ countries, got ${names.length} (is backend/seed reachable?)`);
    const unmapped = names.filter((n) => !isBucket(n) && n !== "" && groupOf(n) === "other");
    assert.deepEqual(unmapped, [], `unmapped in seed data: ${unmapped.join(", ")}`);
    const noCode = names.filter((n) => !isBucket(n) && countryCode(n) === null);
    assert.deepEqual(noCode, [], `no ISO code for: ${noCode.join(", ")}`);
  });

  it("only the buckets land in Other", () => {
    assert.equal(groupOf("International"), "other");
    assert.equal(groupOf("Africa"), "africa");
    assert.equal(groupOf("Atlantis"), "other"); // a name nobody mapped is not guessed
  });

  it("spot checks of the judgement calls", () => {
    const expect: Record<string, string> = {
      Canada: "north-america", "United States": "north-america", Mexico: "north-america",
      Cuba: "central-america-caribbean", Panama: "central-america-caribbean", "Trinidad and Tobago": "central-america-caribbean",
      Brazil: "south-america", Japan: "asia", India: "asia", Georgia: "asia",
      "Saudi Arabia": "middle-east", Turkey: "middle-east", Israel: "middle-east", Iran: "middle-east",
      Australia: "oceania", Fiji: "oceania", Russia: "europe", Cyprus: "europe", Kosovo: "europe",
      "South Africa": "south-africa", Zimbabwe: "sadc", Kenya: "africa", Egypt: "africa",
      Monaco: "europe", "North Macedonia": "europe", "San Marino": "europe",
      Tajikistan: "asia", Turkmenistan: "asia", Myanmar: "asia",
      "Puerto Rico": "central-america-caribbean", Greenland: "north-america",
      Macau: "asia", "New Caledonia": "oceania", "Réunion": "africa",
    };
    for (const [name, group] of Object.entries(expect)) assert.equal(groupOf(name), group, name);
  });

  it("places Monaco, North Macedonia, San Marino, Tajikistan, Turkmenistan and Myanmar", () => {
    const places: Record<string, { code: string; flag: string; tier: string; group: string }> = {
      Monaco: { code: "MC", flag: "🇲🇨", tier: "europe", group: "europe" },
      "North Macedonia": { code: "MK", flag: "🇲🇰", tier: "europe", group: "europe" },
      "San Marino": { code: "SM", flag: "🇸🇲", tier: "europe", group: "europe" },
      Tajikistan: { code: "TJ", flag: "🇹🇯", tier: "asia", group: "asia" },
      Turkmenistan: { code: "TM", flag: "🇹🇲", tier: "asia", group: "asia" },
      Myanmar: { code: "MM", flag: "🇲🇲", tier: "asia", group: "asia" },
    };
    for (const [name, place] of Object.entries(places)) {
      assert.equal(countryCode(name), place.code, name);
      assert.equal(countryFlag(name), place.flag, name);
      assert.equal(tierOf(name), place.tier, name);
      assert.equal(groupOf(name), place.group, name);
    }
  });

  it("places the 2026-10-10 territories with a flag, a code and a landing tier", () => {
    const places: Record<string, { code: string; flag: string; tier: string }> = {
      "Puerto Rico": { code: "PR", flag: "🇵🇷", tier: "north-america" },
      Greenland: { code: "GL", flag: "🇬🇱", tier: "north-america" },
      Macau: { code: "MO", flag: "🇲🇴", tier: "asia" },
      "New Caledonia": { code: "NC", flag: "🇳🇨", tier: "oceania" },
      "Réunion": { code: "RE", flag: "🇷🇪", tier: "africa" },
    };
    for (const [name, place] of Object.entries(places)) {
      assert.equal(countryCode(name), place.code, name);
      assert.equal(countryFlag(name), place.flag, name);
      assert.equal(tierOf(name), place.tier, name);
      assert.notEqual(groupOf(name), "other", name);
    }
    // Réunion is an African territory, so it is not given a world-region code.
    assert.equal(worldRegionOf("RE"), null);
    assert.equal(worldRegionOf("NC"), "oceania");
    assert.equal(worldRegionOf("PR"), "central-america-caribbean");
    assert.equal(worldRegionOf("GL"), "north-america");
    assert.equal(worldRegionOf("MO"), "asia");
  });

  it("Canada is one entry inside North America, not a group of its own", () => {
    assert.ok(!WORLD_REGIONS.some((r) => (r.label as string) === "Canada"));
    assert.equal(groupOf("Canada"), "north-america");
  });
});
