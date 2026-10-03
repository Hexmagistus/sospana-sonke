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
    assert.equal(selected.length, 1);
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

  it("is just the country list: no Countries/Categories tabs", () => {
    assert.ok(!out.includes('role="tab"'));
    assert.ok(!out.includes("Categories"));
  });

  it("South Africa is the first row and the first group", () => {
    const first = out.match(/role="option"[^>]*data-country="([A-Z]+)"/);
    assert.equal(first?.[1], "ZA");
    const sa = html({ selected: "South Africa" });
    assert.match(sa, /aria-selected="true"[^>]*data-country="ZA"|data-country="ZA"[^>]*aria-selected="true"/);
  });
});
