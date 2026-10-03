import "./testPaths";
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { CategorySelect, categoryOptionText } from "./CategorySelect";
import { SidebarResizer } from "./SidebarResizer";
import { countryFromDirectoryLink, DEFAULT_DIRECTORY_COUNTRY } from "../directoryFilters";

const options = [
  { id: "all", label: "All", count: null },
  { id: "listed", label: "Listed", count: null },
  { id: "Municipality", label: "Municipalities", count: 262 },
  { id: "SOE", label: "State-owned", count: 1430 },
];

describe("CategorySelect", () => {
  const out = renderToStaticMarkup(createElement(CategorySelect, { options, value: "Municipality", onChange: () => {}, scope: "South Africa" }));

  it("is one labelled native select with counts in the option text", () => {
    assert.equal((out.match(/<select/g) ?? []).length, 1);
    assert.match(out, /<label[^>]*>Category<\/label>/);
    assert.match(out, /Municipalities 262/);
    assert.match(out, /State-owned 1,430/);
  });

  it("marks the chosen option and says which country the counts are for", () => {
    assert.match(out, /<option value="Municipality" selected="">/);
    assert.match(out, /Counts are for South Africa/);
  });

  it("options without a count show just the label", () => {
    assert.equal(categoryOptionText(options[0]), "All");
    assert.equal(categoryOptionText(options[2]), "Municipalities 262");
  });
});

describe("SidebarResizer", () => {
  const out = renderToStaticMarkup(createElement(SidebarResizer, { width: 320, onChange: () => {}, containerRef: { current: null }, controls: "side" }));

  it("is a focusable vertical separator with value, min and max", () => {
    assert.match(out, /role="separator"/);
    assert.match(out, /aria-orientation="vertical"/);
    assert.match(out, /aria-valuenow="320"/);
    assert.match(out, /aria-valuemin="240"/);
    assert.match(out, /aria-valuemax="480"/);
    assert.match(out, /tabindex="0"/);
    assert.match(out, /aria-controls="side"/);
  });

  it("is hidden below the lg breakpoint (not on mobile)", () => {
    assert.match(out, /class="[^"]*\bhidden\b[^"]*\blg:block\b/);
  });
});

describe("default country", () => {
  it("a bare URL with nothing saved opens on South Africa", () => {
    assert.equal(
      countryFromDirectoryLink({ current: DEFAULT_DIRECTORY_COUNTRY, urlCountry: null, storedCountry: null }),
      "South Africa",
    );
  });
});
