import "./testPaths";
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { CountrySidebar } from "./CountrySidebar";
import { buildCountryRows } from "../countryExplorer";

const rows = buildCountryRows(
  {
    employers: { "Kenya": 122, "South Africa": 1026, "Zimbabwe": 197, "Germany": 5, "Nigeria": 144 },
    counted: { "South Africa": 230, "Germany": 5 },
  },
  { includeEmptyAfrican: true },
);

const html = (props: Partial<Parameters<typeof CountrySidebar>[0]> = {}) =>
  renderToStaticMarkup(createElement(CountrySidebar, { rows, selected: "Kenya", onSelect: () => {}, ...props }));

const pos = (markup: string, needle: string) => {
  const i = markup.indexOf(needle);
  assert.ok(i >= 0, `missing ${needle}`);
  return i;
};

describe("CountrySidebar markup", () => {
  const out = html();

  it("group headers appear in the fixed order", () => {
    const order = ["South Africa</span>", "Rest of SADC</span>", "Rest of Africa</span>", "Other regions</span>"].map((n) => pos(out, n));
    assert.deepEqual([...order].sort((a, b) => a - b), order);
  });

  it("countries inside the groups follow the order too", () => {
    const a = pos(out, ">South Africa<");
    const b = pos(out, ">Zimbabwe<");
    const c = pos(out, ">Kenya<");
    const d = pos(out, ">Germany<");
    assert.ok(a < b && b < c && c < d);
  });

  it("only the selected country is aria-selected", () => {
    const selected = out.match(/aria-selected="true"/g) ?? [];
    // one option plus the active tab
    assert.equal(selected.length, 2);
    assert.match(out, /role="option"[^>]*aria-selected="true"[^>]*data-country="KE"|aria-selected="true"[^>]*role="option"[^>]*data-country="KE"/);
  });

  it("is a listbox per group with options, not a pile of links", () => {
    assert.equal((out.match(/role="listbox"/g) ?? []).length, 4);
    assert.ok((out.match(/role="option"/g) ?? []).length >= 5);
  });

  it("countries with no employers are dimmed and aria-disabled, with an honest label", () => {
    assert.match(out, /aria-disabled="true"/);
    assert.match(out, /No employers yet/);
  });

  it("shows the real count and the small counted badge only where there is one", () => {
    assert.match(out, /1,026 employers/);
    assert.match(out, /230 counted/);
    assert.equal((out.match(/ counted</g) ?? []).length, 2); // South Africa and Germany
  });

  it("heading count is the number of countries that have employers", () => {
    assert.match(out, /Countries \(5\)/);
  });

  it("one tab stop for the list: the selected option", () => {
    const stops = out.match(/role="option"[^>]*tabindex="0"/g) ?? [];
    assert.equal(stops.length, 1);
    assert.match(stops[0], /KE|tabindex/);
  });

  it("has a labelled search box and an All countries reset", () => {
    assert.match(out, /Search countries/);
    assert.match(out, /All countries/);
  });

  it("a folded group hides its rows but keeps its header", () => {
    const folded = html({ initialCollapsed: ["sadc"] });
    assert.ok(!folded.includes(">Zimbabwe<"));
    assert.match(folded, /Rest of SADC/);
    assert.match(folded, /aria-expanded="false"/);
  });

  it("Categories tab appears only when categories are given", () => {
    assert.ok(!out.includes("Categories"));
    const withCats = html({ categories: [{ id: "all", label: "All", count: null }, { id: "SOE", label: "State-owned", count: 4 }], selectedCategory: "SOE", initialTab: "categories" });
    assert.match(withCats, /Categories \(2\)/);
    assert.match(withCats, /State-owned/);
  });
});
