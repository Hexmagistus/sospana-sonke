import "./testPaths";
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { CountrySidebar } from "./CountrySidebar";
import { GROUPS, buildCountryRows } from "../countryExplorer";

const rows = buildCountryRows(
  {
    employers: { "Kenya": 122, "South Africa": 1026, "Zimbabwe": 197, "Germany": 5, "Nigeria": 144, "Canada": 4, "Japan": 2 },
    counted: { "South Africa": 230, "Germany": 5 },
  },
  { includeEmptyAfrican: true },
);

const ALL_OPEN = GROUPS.map((g) => g.id);
// Every group starts folded in real use, so most checks open them all explicitly.
const html = (props: Partial<Parameters<typeof CountrySidebar>[0]> = {}) =>
  renderToStaticMarkup(createElement(CountrySidebar, { rows, selected: "Kenya", onSelect: () => {}, initialExpanded: ALL_OPEN, ...props }));

const pos = (markup: string, needle: string) => {
  const i = markup.indexOf(needle);
  assert.ok(i >= 0, `missing ${needle}`);
  return i;
};

describe("CountrySidebar markup", () => {
  const out = html();

  it("group headers appear in the fixed order", () => {
    const order = ["South Africa</span>", "Rest of SADC</span>", "Rest of Africa</span>", "Europe</span>", "North America</span>", "Asia</span>"].map((n) => pos(out, n));
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
    assert.equal((out.match(/role="listbox"/g) ?? []).length, 6);
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
    assert.match(out, /Countries \(7\)/);
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
    const folded = html({ initialExpanded: ALL_OPEN.filter((g) => g !== "sadc") });
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

  it("every group starts collapsed by default, the selected country's group included", () => {
    const fresh = html({ initialExpanded: undefined, selected: "South Africa" });
    assert.equal((fresh.match(/aria-expanded="false"/g) ?? []).length, 6);
    assert.ok(!fresh.includes('aria-expanded="true"'));
    assert.ok(!fresh.includes('role="option"'), "no country rows until a group is opened");
    assert.ok(!fresh.includes('role="listbox"'));
    // the header still tells you where the selection is
    assert.match(fresh, /contains the selected country, South Africa/);
    // every group header is there, with its count
    for (const label of ["South Africa", "Rest of SADC", "Rest of Africa", "Europe", "North America", "Asia"]) {
      assert.ok(fresh.includes(`${label}`), label);
    }
  });

  it("only the clicked group's rows are rendered when one is opened", () => {
    const one = html({ initialExpanded: ["north-america"], selected: "South Africa" });
    assert.equal((one.match(/aria-expanded="true"/g) ?? []).length, 1);
    assert.ok(one.includes(">Canada<"));
    assert.ok(!one.includes(">Kenya<"));
    assert.ok(!one.includes(">Germany<"));
  });

  it("North America holds Canada", () => {
    const na = html({ initialExpanded: ["north-america"] });
    assert.match(na, /data-country="CA"/);
  });
});
