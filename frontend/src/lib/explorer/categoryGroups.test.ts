import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, it } from "node:test";
import {
  ALIASES, CATEGORY_GROUPS, EXPLORER_NAV, canonicalType, storedCode, MAX_PAGES, NO_EMPLOYERS_YET, PAGE_SIZE, emptyStateFor, fetchGroupRows, groupByName,
  groupCategoryOptions, groupListPath, groupOfType, rowsInCategory, shownRows, typeBadgeFor,
} from "./categoryGroups";
import { isExplorerPath } from "./explorerPaths";
import { buildCountryRows } from "../countryExplorer";

const src = (...p: string[]) => readFileSync(join(process.cwd(), "src", ...p), "utf8");
const codes = (name: Parameters<typeof groupByName>[0]) => groupByName(name).types.map((t) => t.code);

type R = { id: string; company_name: string; country: string; source_type: string; careers_url: string | null };
const row = (id: string, country: string, source_type: string, careers_url: string | null = null, name = id): R =>
  ({ id, company_name: name, country, source_type, careers_url });

describe("category groups: mapping", () => {
  it("maps the stored source_type codes into the explorer pages", () => {
    assert.deepEqual(codes("universities"), ["UNI"]);
    assert.deepEqual(codes("colleges"), ["COLLEGE", "SETA"]);
    assert.deepEqual(codes("hospitals"), ["HOSPITAL"]);
    assert.deepEqual(codes("ngos"), ["NGO"]);
    assert.deepEqual(codes("government"), ["DEPT", "MUNI", "SOE"]);
  });

  it("no code is on two pages; codes for /companies only belong to no group", () => {
    const all = CATEGORY_GROUPS.flatMap((g) => g.types.map((t) => t.code));
    assert.equal(all.length, new Set(all).size);
    for (const c of ["PRIVATE", "JSE", "SPORT", "FED", "MUSIC", "", null]) assert.equal(groupOfType(c as string), null, String(c));
    assert.equal(groupOfType("soe")?.path, "/government");
    assert.equal(groupOfType("SETA")?.path, "/colleges");
  });

  it("menu and landing order: Companies, Universities, Colleges & SETAs, Hospitals, NGOs, Government", () => {
    assert.deepEqual(EXPLORER_NAV.map((l) => l.label), ["Companies", "Universities", "Colleges & SETAs", "Hospitals", "NGOs", "Government"]);
    assert.deepEqual(EXPLORER_NAV.map((l) => l.href), ["/companies", "/universities", "/colleges", "/hospitals", "/ngos", "/government"]);
  });

  it("a row's badge names its own category; an unexpected code is shown as is", () => {
    const gov = groupByName("government");
    assert.equal(typeBadgeFor(gov, "MUNI").label, "Municipality");
    assert.equal(typeBadgeFor(gov, "soe").label, "State-owned");
    assert.equal(typeBadgeFor(gov, "XYZ").label, "XYZ");
  });
});

describe("category groups: aliases (labels other than the canonical code)", () => {
  it("labels such as Government, Municipality, TVET College land on the right page under the right code", () => {
    const cases: [string, string, string][] = [
      ["NGO", "NGO", "/ngos"], ["Government", "DEPT", "/government"], ["Municipality", "MUNI", "/government"],
      ["SOE", "SOE", "/government"], ["TVET College", "COLLEGE", "/colleges"], ["SETA", "SETA", "/colleges"],
      ["PARASTATAL", "SOE", "/government"], ["npo", "NGO", "/ngos"], ["MUNICIPALI", "MUNI", "/government"],
    ];
    for (const [label, code, path] of cases) {
      assert.equal(canonicalType(label), code, label);
      assert.equal(groupOfType(label)?.path, path, label);
    }
    assert.equal(storedCode("TVET College"), "TVET COLLE");
    assert.equal(canonicalType("zse"), "ZSE");
  });

  it("every alias points at a code on one of the pages, and none hides a /companies-only code", () => {
    const canonical = new Set(CATEGORY_GROUPS.flatMap((g) => g.types.map((t) => t.code)));
    for (const [label, code] of Object.entries(ALIASES)) {
      assert.ok(canonical.has(code), label);
      assert.ok(!["JSE", "PRIVATE", "SPORT", "FED", "MUSIC"].includes(storedCode(label)), label);
    }
  });

  it("alias rows are filtered, counted and badged under their code", () => {
    const gov = groupByName("government");
    const rows = [row("1", "South Africa", "SOE"), row("2", "South Africa", "PARASTATAL"), row("3", "South Africa", "MUNICIPALI")];
    assert.deepEqual(rowsInCategory(rows, "SOE").map((r) => r.id), ["1", "2"]);
    assert.deepEqual(groupCategoryOptions(gov, rows, "South Africa").map((o) => o.count), [3, 0, 1, 2]);
    assert.equal(typeBadgeFor(gov, "PARASTATAL").label, "State-owned");
  });
});

describe("category groups: fetching", () => {
  it("asks for one group, active rows, at most the API's per-request cap", () => {
    assert.equal(groupListPath("ngos"), `/companies?group=ngos&active=true&limit=${PAGE_SIZE}`);
    assert.equal(groupListPath("government", 1500), "/companies?group=government&active=true&limit=1500&offset=1500");
  });

  it("pages through a group bigger than one request and stops on a short page", async () => {
    const calls: string[] = [];
    const rows = await fetchGroupRows("government", async (p) => {
      calls.push(p);
      return calls.length === 1 ? Array.from({ length: PAGE_SIZE }, (_, i) => i) : [1, 2, 3];
    });
    assert.equal(rows.length, PAGE_SIZE + 3);
    assert.equal(calls.length, 2);
    assert.match(calls[1], /offset=1500/);
  });

  it("an empty group is one request and no rows (nothing invented)", async () => {
    let n = 0;
    const rows = await fetchGroupRows("ngos", async () => { n++; return []; });
    assert.deepEqual(rows, []);
    assert.equal(n, 1);
  });

  it("never loops forever", async () => {
    let n = 0;
    await fetchGroupRows("colleges", async () => { n++; return Array.from({ length: PAGE_SIZE }, () => 0); });
    assert.equal(n, MAX_PAGES);
  });
});

describe("category groups: what the page shows", () => {
  const rows: R[] = [
    row("1", "South Africa", "COLLEGE", "https://a.example", "Zeta College"),
    row("2", "South Africa", "SETA", null, "Alpha SETA"),
    row("3", "South Africa", "COLLEGE", null, "Beta College"),
    row("4", "Kenya", "COLLEGE", "https://k.example", "Kenya College"),
  ];

  it("filters by category, country and search; careers links first, then A-Z", () => {
    const base = { category: "all", country: "South Africa", q: "", shortlistOnly: false, shortlistIds: new Set<string>() };
    assert.deepEqual(shownRows(rows, base).map((r) => r.id), ["1", "2", "3"]);
    assert.deepEqual(shownRows(rows, { ...base, category: "SETA" }).map((r) => r.id), ["2"]);
    assert.deepEqual(shownRows(rows, { ...base, country: "" }).map((r) => r.id), ["4", "1", "2", "3"]);
    assert.deepEqual(shownRows(rows, { ...base, q: "beta" }).map((r) => r.id), ["3"]);
    assert.deepEqual(shownRows(rows, { ...base, shortlistOnly: true, shortlistIds: new Set(["4"]) }).map((r) => r.id), ["4"]);
    assert.equal(rowsInCategory(rows, "COLLEGE").length, 3);
  });

  it("the category menu counts each code for the country on screen", () => {
    assert.deepEqual(groupCategoryOptions(groupByName("colleges"), rows, "South Africa"), [
      { id: "all", label: "All colleges & SETAs", count: 3 },
      { id: "COLLEGE", label: "Colleges (TVET, public & private)", count: 2 },
      { id: "SETA", label: "SETAs", count: 1 },
    ]);
    assert.equal(groupCategoryOptions(groupByName("colleges"), rows, "")[0].count, 4);
  });

  it("an empty country says No employers listed here yet, never invents rows or says no jobs", () => {
    const e = emptyStateFor(groupByName("ngos"), { shortlistOnly: false, q: "", country: "Malawi", category: "all" });
    assert.equal(e.title, NO_EMPLOYERS_YET);
    assert.equal(NO_EMPLOYERS_YET, "No employers listed here yet");
    assert.match(e.message, /We have no NGOs and non-profits in Malawi in the directory yet/);
    assert.doesNotMatch(e.message, /no jobs|no vacancies/i);
    const m = emptyStateFor(groupByName("government"), { shortlistOnly: false, q: "", country: "Kenya", category: "MUNI" });
    assert.match(m.message, /no municipalities or metros in Kenya/);
    assert.match(m.message, /or category/);
    assert.equal(emptyStateFor(groupByName("ngos"), { shortlistOnly: false, q: "red", country: "", category: "all" }).title, "No matches");
  });

  it("countries keep the standing order: South Africa, rest of SADC, rest of Africa, then other regions", () => {
    const r = buildCountryRows({ employers: { Brazil: 2, Kenya: 3, Zambia: 1, "South Africa": 5 } }).filter((x) => x.employers > 0);
    assert.deepEqual(r.map((x) => x.name), ["South Africa", "Zambia", "Kenya", "Brazil"]);
  });
});

describe("category groups: pages and navigation", () => {
  it("each page is a thin wrapper around the one shared explorer (no duplicated page logic)", () => {
    for (const g of CATEGORY_GROUPS) {
      const page = src("app", g.path.slice(1), "page.tsx");
      assert.match(page, new RegExp(`<GroupDirectoryPage name="${g.group}" />`), g.path);
      assert.doesNotMatch(page, /useState|useEffect|api\.get/, g.path);
      assert.ok(page.split("\n").length < 20, g.path);
    }
  });

  it("all six directory pages use the explorer layout and render no ads", () => {
    for (const l of EXPLORER_NAV) assert.equal(isExplorerPath(l.href), true, l.href);
    const shared = src("components", "GroupDirectory.tsx");
    assert.match(shared, /<CountryExplorer/);
    assert.match(shared, /<CategoryListPanel/);
    assert.match(shared, /<HowToUseCard steps=\{steps\} loading/);
    assert.doesNotMatch(shared, /AdSlot|LoginAdRail|\/ads\/slots|Sponsored/);
  });

  it("the phone-fit script (320-414px) checks every directory page", () => {
    const script = readFileSync(join(process.cwd(), "scripts", "mobile-fit.mjs"), "utf8");
    for (const l of EXPLORER_NAV) assert.ok(script.includes(`"${l.href}"`), l.href);
  });

  it("the menu drawer, landing cards and robots list the new pages", () => {
    assert.match(src("components", "Nav.tsx"), /\.\.\.EXPLORER_NAV/);
    const landing = src("app", "page.tsx");
    const hrefs = [...landing.matchAll(/label: "[^"]+", desc: "[^"]+", href: "([^"]+)"/g)].map((m) => m[1]);
    assert.deepEqual(hrefs, EXPLORER_NAV.map((l) => l.href));
    const robots = src("app", "robots.ts");
    for (const l of EXPLORER_NAV) assert.ok(robots.includes(`"${l.href}"`), l.href);
  });
});
