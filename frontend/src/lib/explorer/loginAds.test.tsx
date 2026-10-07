import "./testPaths";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, it } from "node:test";
import { createElement, Fragment } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { LoginAdRail } from "./AdSlot";

// Ads live on the sign-in page only: exactly four spots there, none on the explorer pages.
const src = (...p: string[]) => readFileSync(join(process.cwd(), "src", ...p), "utf8");
const AD_MARKERS = /AdSlot|LoginAdRail|AdColumn|AdApplyDialog|\/ads\/slots|data-slot|Sponsored/;

describe("login is the only page with ads", () => {
  it("the login page renders exactly four spots, LG1-LG4, and no fake ads", () => {
    const page = src("app", "login", "page.tsx");
    assert.equal((page.match(/<LoginAdRail\b/g) ?? []).length, 2, "one rail each side");
    assert.match(page, /<LoginAdRail side="left"/);
    assert.match(page, /<LoginAdRail side="right"/);
    // The ads come only from the approved-ads endpoint; nothing seeded in the page.
    assert.match(page, /api\.get<PublicAd\[\]>\("\/ads\/slots"\)/);
    assert.doesNotMatch(page, /business_name:/);

    const out = renderToStaticMarkup(createElement(Fragment, null,
      createElement(LoginAdRail, { side: "left", ads: [], onApply: () => {} }),
      createElement(LoginAdRail, { side: "right", ads: [], onApply: () => {} })));
    assert.deepEqual([...out.matchAll(/data-slot="([^"]+)"/g)].map((m) => m[1]), ["LG1", "LG2", "LG3", "LG4"]);
    assert.equal((out.match(/Advertise here</g) ?? []).length, 4);
    assert.doesNotMatch(out, />Sponsored</);
  });

  it("on phones and tablets the form comes first and the spots follow it", () => {
    const page = src("app", "login", "page.tsx");
    const form = page.indexOf("<form");
    assert.ok(form > 0);
    assert.ok(page.indexOf('<LoginAdRail side="left"') > form, "left rail after the form in DOM order");
    assert.ok(page.indexOf('<LoginAdRail side="right"') > form, "right rail after the form in DOM order");
    assert.match(page, /xl:col-start-1/);
    assert.match(page, /xl:col-start-3/);
  });

  it("the explorer pages render no ad spots", () => {
    const files = [
      ["components", "CountryExplorer.tsx"],
      ["app", "companies", "page.tsx"],
      ["app", "companies", "layout.tsx"],
      ["app", "universities", "page.tsx"],
      ["app", "colleges", "page.tsx"],
      ["app", "hospitals", "page.tsx"],
      ["app", "ngos", "page.tsx"],
      ["app", "government", "page.tsx"],
      ["components", "GroupDirectory.tsx"],
    ];
    for (const f of files) assert.doesNotMatch(src(...f), AD_MARKERS, f.join("/"));
  });
});
