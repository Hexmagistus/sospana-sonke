import "./testPaths";
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { categoryListItems, splitColumns, vacancyValue } from "./categoryList";
import { CategoryListPanel } from "./CategoryListPanel";
import { categoryChipCount, matchesDirectoryFilter } from "../directoryFilters";
import { isNotCounted } from "../notCounted";

type Row = { id: string; company_name: string; country: string; source_type: string; careers_url: string | null; open_vacancies: number; open_vacancies_known: boolean };
const row = (i: number, over: Partial<Row> = {}): Row => ({
  id: `c${i}`, company_name: `Company ${String.fromCharCode(65 + (i % 26))}${i}`, country: "Australia", source_type: "PRIVATE",
  careers_url: `https://example.com/${i}`, open_vacancies: 0, open_vacancies_known: false, ...over,
});

// 21 private employers, 5 other rows that must not be listed.
const privates: Row[] = Array.from({ length: 21 }, (_, i) => row(i, i % 3 === 0 ? { open_vacancies: i + 1, open_vacancies_known: true } : {}));
const privates2 = [...privates];
privates2[1] = row(1, { company_name: "Atlassian", open_vacancies: 14, open_vacancies_known: true });
privates2[2] = row(2, { company_name: "Canva" }); // link, no count: NCY
privates2[4] = row(4, { company_name: "Zero Co", open_vacancies_known: true }); // counted, really 0
const others = Array.from({ length: 5 }, (_, i) => row(100 + i, { source_type: "SOE" }));
const all = [...others, ...privates2];
const facets = { country_type_counts: { Australia: { PRIVATE: 21, SOE: 5 } } };

const inScope = (rows: Row[], filter: string) => rows.filter((c) => c.country === "Australia" && matchesDirectoryFilter(c, filter));

describe("category list over the map", () => {
  it("lists every company of the category: length equals the dropdown count", () => {
    const items = categoryListItems(inScope(all, "Private"));
    assert.equal(items.length, categoryChipCount(facets, "Australia", "PRIVATE"));
    assert.equal(items.length, 21);
    assert.equal(categoryListItems(inScope(all, "SOE")).length, categoryChipCount(facets, "Australia", "SOE"));
    assert.equal(new Set(items.map((i) => i.id)).size, 21);
  });

  it("'All' lists the whole country", () => {
    assert.equal(categoryListItems(inScope(all, "all")).length, 26);
  });

  it("bracket format: a number when counted (zero included), NCY when not counted", () => {
    const items = categoryListItems(privates2);
    const by = (n: string) => items.find((i) => i.name === n)!;
    assert.equal(by("Atlassian").text, "Atlassian (14)");
    assert.equal(by("Canva").text, "Canva (NCY)");
    assert.equal(by("Zero Co").text, "Zero Co (0)");
    assert.equal(by("Zero Co").counted, true);
    assert.equal(by("Canva").counted, false);
  });

  it("uses the same counted rule as the Not counted yet badge", () => {
    for (const r of privates2) {
      const ncy = vacancyValue(r) === "NCY";
      assert.equal(ncy, isNotCounted(r), r.company_name); // every row here has a careers link
    }
    assert.equal(vacancyValue({ open_vacancies: 3, open_vacancies_known: false }), "3"); // held vacancies count
  });

  it("alphabetical, stable, nothing hidden", () => {
    const names = categoryListItems(privates2).map((i) => i.name);
    assert.deepEqual(names, [...names].sort((a, b) => a.localeCompare(b, "en")));
  });

  it("two columns hold all items once; short lists stay in one column", () => {
    const items = categoryListItems(privates2);
    const [l, r] = splitColumns(items);
    assert.equal(l.length + r.length, 21);
    assert.deepEqual([...l, ...r].map((i) => i.id), items.map((i) => i.id));
    assert.equal(splitColumns(items.slice(0, 5))[1].length, 0);
  });
});

describe("CategoryListPanel markup", () => {
  const items = categoryListItems(privates2);
  const out = renderToStaticMarkup(createElement(CategoryListPanel, { items, category: "Private", country: "Australia" }));
  const text = out.replace(/<[^>]+>/g, "").replace(/&#x27;/g, "'").replace(/\s+/g, " ");

  it("renders exactly one entry per company, equal to the dropdown count", () => {
    assert.equal((out.match(/<li/g) ?? []).length, 21);
    assert.match(out, /data-testid="category-list-count">21</);
  });

  it("shows Name (n) and Name (NCY) as text", () => {
    assert.ok(text.includes("Atlassian (14)"), text);
    assert.ok(text.includes("Canva (NCY)"));
    assert.ok(text.includes("Zero Co (0)"));
  });

  it("NCY carries a tooltip and the legend explains it", () => {
    assert.match(out, /<abbr title="NCY = Not counted yet[^"]*not “no jobs”/);
    assert.match(text, /NCY = Not counted yet, not “no jobs”/);
  });

  it("names open the careers page in a new tab, safely", () => {
    assert.match(out, /<a href="https:\/\/example\.com\/2"[^>]*target="_blank"[^>]*rel="noopener noreferrer"/);
  });

  it("a company without a careers link is plain text, not a dead link", () => {
    const html = renderToStaticMarkup(createElement(CategoryListPanel, {
      items: categoryListItems([row(1, { company_name: "No Link Ltd", careers_url: null })]), category: "Private", country: "Australia",
    }));
    assert.ok(!html.includes("<a "));
    assert.match(html.replace(/<[^>]+>/g, ""), /No Link Ltd \(NCY\)/);
  });

  it("is a labelled region, scrollable, over the map from md up and under it on small screens", () => {
    assert.match(out, /aria-label="Private companies in Australia"/);
    assert.match(out, /md:absolute/);
    assert.match(out, /overflow-y-auto/);
    assert.match(out, /max-h-72/); // small-screen box scrolls
  });

  it("renders nothing for an empty category", () => {
    assert.equal(renderToStaticMarkup(createElement(CategoryListPanel, { items: [], category: "Private", country: "Australia" })), "");
  });
});

describe("matchesDirectoryFilter", () => {
  it("matches the category filters the cards use", () => {
    assert.equal(matchesDirectoryFilter({ source_type: "muni" }, "Municipality"), true);
    assert.equal(matchesDirectoryFilter({ source_type: "PRIVATE" }, "SOE"), false);
    assert.equal(matchesDirectoryFilter({ source_type: "JSE" }, "listed"), true);
    assert.equal(matchesDirectoryFilter({ source_type: "DEPT" }, "listed"), true);
    assert.equal(matchesDirectoryFilter({ source_type: "SOE" }, "listed"), false);
    assert.equal(matchesDirectoryFilter({ source_type: null }, "all"), true);
  });
});
