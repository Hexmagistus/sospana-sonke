import "./testPaths";
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { CategorySelect, categoryOptionText } from "./CategorySelect";
import { SidebarResizer } from "./SidebarResizer";
import { countryFromDirectoryLink, DEFAULT_DIRECTORY_COUNTRY, DIRECTORY_GUIDE_STEPS, guideStepsFor } from "../directoryFilters";
import { HowToUseCard } from "./HowToUseCard";

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

describe("HowToUseCard (hero banner)", () => {
  const open = renderToStaticMarkup(createElement(HowToUseCard, { steps: guideStepsFor(true), initialOpen: true }));

  it("shows the existing guide wording as a numbered list", () => {
    assert.match(open, /aria-label="How to use"/);
    assert.equal((open.match(/<li/g) ?? []).length, DIRECTORY_GUIDE_STEPS.length);
    assert.match(open, /<ol/);
    for (const step of DIRECTORY_GUIDE_STEPS) assert.ok(open.includes(step.replace("'", "&#x27;")) || open.includes(step), step);
    assert.match(open, />Hide</);
  });

  it("uses the theme tokens (bright card, dark text by default), never fixed navy or white", () => {
    assert.match(open, /bg-ss-panel/);
    assert.match(open, /text-ss-text/);
    assert.ok(!open.includes("bg-[#071528]"));
    assert.ok(!open.includes("text-white"));
  });

  it("when hidden, only a small How to use button remains", () => {
    const hidden = renderToStaticMarkup(createElement(HowToUseCard, { steps: guideStepsFor(true), initialOpen: false }));
    assert.match(hidden, /<button[^>]*>How to use<\/button>/);
    assert.ok(!hidden.includes("<ol"));
  });

  it("renders nothing until the saved choice is read (no flash)", () => {
    assert.equal(renderToStaticMarkup(createElement(HowToUseCard, { steps: guideStepsFor(true) })), "");
  });

  it("pages without a category menu drop the category step", () => {
    assert.equal(guideStepsFor(true).length, 4);
    const no = guideStepsFor(false);
    assert.equal(no.length, 3);
    assert.ok(!no.some((s) => /category/i.test(s)));
    assert.match(no[0], /country/i);
  });
});
