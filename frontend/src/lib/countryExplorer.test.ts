import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  AFRICAN_COUNTRY_NAMES, buildCountryRows, groupRows, listedCountryCount, navigableRows,
  countryFromQuery, regionLabel, searchForSelection, type GroupId,
} from "./countryExplorer";
import { countryCode, countryFlag, KNOWN_COUNTRY_NAMES, resolveCountryParam } from "./countryCodes";
import { MIN_VIEW_W, WORLD_VIEW, countryBox, easeInOutCubic, mixViews, viewForCountry } from "./mapView";

const EMPLOYERS: Record<string, number> = {
  "United States": 328, "Kenya": 122, "Zimbabwe": 197, "South Africa": 1026, "Botswana": 148,
  "Africa": 9, "Nigeria": 144, "Brazil": 68, "Angola": 90, "International": 5, "Australia": 30,
  "Côte d'Ivoire": 69, "Eswatini": 126, "Germany": 5,
};

describe("country list order: South Africa, SADC, Africa, others", () => {
  const rows = buildCountryRows({ employers: EMPLOYERS });
  const groups = groupRows(rows);

  it("groups come out in the fixed order with the fixed names", () => {
    assert.deepEqual(groups.map((g) => g.label), ["South Africa", "Rest of SADC", "Rest of Africa", "Other regions"]);
    assert.deepEqual(groups.map((g) => g.id), ["south-africa", "sadc", "africa", "other"]);
  });

  it("South Africa is the first row of the whole list", () => {
    assert.equal(rows[0].name, "South Africa");
    assert.equal(groups[0].rows.length, 1);
  });

  it("SADC rows are SADC members only, then Africa rows, then everything else", () => {
    assert.deepEqual(groups[1].rows.map((r) => r.name), ["Angola", "Botswana", "Eswatini", "Zimbabwe"]);
    assert.deepEqual(groups[2].rows.map((r) => r.name), ["Africa", "Côte d'Ivoire", "Kenya", "Nigeria"]);
    assert.deepEqual(groups[3].rows.map((r) => r.name), ["Australia", "Brazil", "Germany", "International", "United States"]);
  });

  it("the order does not depend on counts or on the order the API sent them", () => {
    const shuffled = Object.fromEntries(Object.entries(EMPLOYERS).reverse());
    assert.deepEqual(buildCountryRows({ employers: shuffled }).map((r) => r.name), rows.map((r) => r.name));
  });

  it("a search keeps the order and drops empty groups", () => {
    const g = groupRows(rows, "ni");
    assert.deepEqual(g.map((x) => x.id), ["sadc", "africa", "other"]);
    assert.deepEqual(g.flatMap((x) => x.rows.map((r) => r.name)), ["Eswatini", "Nigeria", "United States"]);
    const accent = groupRows(rows, "cote");
    assert.deepEqual(accent.flatMap((x) => x.rows.map((r) => r.name)), ["Côte d'Ivoire"]);
    assert.deepEqual(groupRows(rows, "zz-nothing"), []);
  });

  it("the heading count is countries with employers, not buckets", () => {
    assert.equal(listedCountryCount(rows), EMPLOYERS_COUNTRIES);
  });

  it("region labels follow the same tiers", () => {
    assert.equal(regionLabel("South Africa"), "South Africa");
    assert.equal(regionLabel("Zimbabwe"), "Rest of SADC");
    assert.equal(regionLabel("Kenya"), "Rest of Africa");
    assert.equal(regionLabel("Germany"), "Europe");
    assert.equal(regionLabel("Brazil"), "South America");
    assert.equal(regionLabel("Africa"), "Africa-wide");
  });
});
const EMPLOYERS_COUNTRIES = Object.keys(EMPLOYERS).filter((n) => n !== "Africa" && n !== "International").length;

describe("countries with no employers", () => {
  const rows = buildCountryRows({ employers: { "South Africa": 10, "Kenya": 3 } }, { includeEmptyAfrican: true });
  const ghana = rows.find((r) => r.name === "Ghana");

  it("African states with none are listed, dimmed and not selectable", () => {
    assert.ok(ghana);
    assert.equal(ghana!.employers, 0);
    assert.equal(ghana!.selectable, false);
    assert.equal(rows.find((r) => r.name === "Kenya")!.selectable, true);
    assert.equal(rows.length, new Set(AFRICAN_COUNTRY_NAMES).size);
  });

  it("they are skipped by keyboard navigation and are not counted in the heading", () => {
    const groups = groupRows(rows);
    const nav = navigableRows(groups, new Set<GroupId>(), false).map((r) => r.name);
    assert.deepEqual(nav, ["South Africa", "Kenya"]);
    assert.equal(listedCountryCount(rows), 2);
  });

  it("a folded group leaves the keyboard order, unless a search is open", () => {
    const groups = groupRows(rows);
    assert.deepEqual(navigableRows(groups, new Set<GroupId>(["africa"]), false).map((r) => r.name), ["South Africa"]);
    assert.deepEqual(navigableRows(groups, new Set<GroupId>(["africa"]), true).map((r) => r.name), ["South Africa", "Kenya"]);
  });

  it("without the option, only countries with employers appear", () => {
    assert.equal(buildCountryRows({ employers: { "Kenya": 3, "Chad": 0 } }).length, 1);
  });
});

describe("real numbers only", () => {
  it("counts come through unchanged and missing ones are 0, never guessed", () => {
    const rows = buildCountryRows({
      employers: { "South Africa": 1026, "Kenya": 122 },
      withLinks: { "South Africa": 748 },
      counted: { "South Africa": 230 },
      openVacancies: { "South Africa": 2867 },
    });
    const sa = rows.find((r) => r.name === "South Africa")!;
    assert.deepEqual([sa.employers, sa.withLinks, sa.counted, sa.openVacancies], [1026, 748, 230, 2867]);
    const ke = rows.find((r) => r.name === "Kenya")!;
    assert.deepEqual([ke.employers, ke.withLinks, ke.counted, ke.openVacancies], [122, 0, 0, 0]);
  });
});

describe("selection and the URL", () => {
  it("picking a country writes its short code", () => {
    assert.equal(searchForSelection("", "South Africa"), "?country=ZA");
    assert.equal(searchForSelection("?country=ZA", "Kenya"), "?country=KE");
    assert.equal(searchForSelection("", "Côte d'Ivoire"), "?country=CI");
    assert.equal(searchForSelection("", "Africa"), "?country=AFRICA");
  });

  it("other params stay, ?company= goes, All countries writes ?country=all", () => {
    assert.equal(searchForSelection("?type=SOE&country=ZA", "Nigeria"), "?type=SOE&country=NG");
    assert.equal(searchForSelection("?company=abc&country=ZA", "Nigeria"), "?country=NG");
    assert.equal(searchForSelection("?type=SOE&country=ZA", ""), "?type=SOE&country=all");
    assert.equal(searchForSelection("?country=ZA", ""), "?country=all");
  });

  it("a code or a name in the URL selects the same country (refresh and old links work)", () => {
    for (const raw of ["ZA", "za", "South Africa", "south africa"]) {
      assert.equal(resolveCountryParam(raw, KNOWN_COUNTRY_NAMES), "South Africa");
    }
    assert.equal(resolveCountryParam("CI", KNOWN_COUNTRY_NAMES), "Côte d'Ivoire");
    assert.equal(resolveCountryParam("AFRICA", KNOWN_COUNTRY_NAMES), "Africa");
    assert.equal(resolveCountryParam("XK", KNOWN_COUNTRY_NAMES), "Kosovo");
  });

  it("?country=all is All countries, absent is not", () => {
    assert.equal(countryFromQuery("all", KNOWN_COUNTRY_NAMES), "");
    assert.equal(countryFromQuery("ALL", KNOWN_COUNTRY_NAMES), "");
    assert.equal(countryFromQuery(null, KNOWN_COUNTRY_NAMES), null);
    assert.equal(countryFromQuery("ZA", KNOWN_COUNTRY_NAMES), "South Africa");
    assert.equal(countryFromQuery("nonsense", KNOWN_COUNTRY_NAMES), null);
  });

  it("a typo selects nothing", () => {
    assert.equal(resolveCountryParam("ZZ", KNOWN_COUNTRY_NAMES), null);
    assert.equal(resolveCountryParam("Narnia", KNOWN_COUNTRY_NAMES), null);
    assert.equal(resolveCountryParam("", KNOWN_COUNTRY_NAMES), null);
    assert.equal(resolveCountryParam(null, KNOWN_COUNTRY_NAMES), null);
  });

  it("selection -> URL -> selection round-trips for every known country", () => {
    for (const name of KNOWN_COUNTRY_NAMES) {
      const search = searchForSelection("", name);
      const raw = new URLSearchParams(search).get("country");
      assert.equal(resolveCountryParam(raw, KNOWN_COUNTRY_NAMES), name, name);
    }
  });

  it("codes are unique across the directory", () => {
    const seen = new Map<string, string>();
    for (const name of KNOWN_COUNTRY_NAMES) {
      const code = countryCode(name);
      assert.ok(code, `no code for ${name}`);
      assert.ok(!seen.has(code!), `${name} and ${seen.get(code!)} share ${code}`);
      seen.set(code!, name);
    }
  });

  it("every country gets its own flag, buckets get a globe", () => {
    assert.equal(countryFlag("South Africa"), "🇿🇦");
    assert.equal(countryFlag("Kosovo"), "🇽🇰");
    assert.equal(countryFlag("Peru"), "🇵🇪");
    assert.equal(countryFlag("Africa"), "🌍");
    assert.equal(countryFlag("International"), "🌐");
  });
});

describe("map camera", () => {
  const square = "M100,100L140,100L140,140L100,140Z";
  it("frames a country inside the world with the map's aspect ratio", () => {
    const v = viewForCountry(square, { x: 120, y: 120 });
    assert.ok(Math.abs(v.w / v.h - 960 / 500) < 1e-9);
    assert.ok(v.x >= 0 && v.y >= 0 && v.x + v.w <= 960 && v.y + v.h <= 500);
    assert.ok(v.w >= MIN_VIEW_W);
    assert.ok(v.x <= 100 && v.x + v.w >= 140, "country is inside the view");
  });
  it("does not zoom a tiny island into a blur", () => {
    assert.equal(viewForCountry("M10,10L11,10L11,11Z", { x: 10, y: 10 }).w, MIN_VIEW_W);
  });
  it("keeps far-away pieces out of the frame", () => {
    const d = "M100,100L180,100L180,160L100,160ZM600,300L610,300L610,310Z";
    const box = countryBox(d)!;
    assert.equal(box.maxX, 180);
  });
  it("easing and mixing hit their ends", () => {
    assert.equal(easeInOutCubic(0), 0);
    assert.equal(easeInOutCubic(1), 1);
    assert.deepEqual(mixViews(WORLD_VIEW, { x: 10, y: 10, w: 100, h: 50 }, 1), { x: 10, y: 10, w: 100, h: 50 });
    assert.deepEqual(mixViews(WORLD_VIEW, { x: 10, y: 10, w: 100, h: 50 }, 0), WORLD_VIEW);
  });
});
