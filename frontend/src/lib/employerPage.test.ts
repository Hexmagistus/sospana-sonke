import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it } from "node:test";
import { categoryLabel, checkedText, employerPath, storedScopeText, urlScopeText } from "./employerPage.js";

describe("public employer pages", () => {
  it("keeps the employer id in the public path", () => {
    assert.equal(employerPath("abc"), "/employers/abc");
  });

  it("names a category in words and leaves an unknown code as itself", () => {
    assert.equal(categoryLabel("HOSPITAL"), "Hospital");
    assert.equal(categoryLabel("PARASTATAL"), "State-owned");
    assert.equal(categoryLabel("ZZZ"), "ZZZ");
  });

  it("says global only when the row is marked global", () => {
    assert.match(storedScopeText("global"), /global careers board/);
    assert.match(storedScopeText(null), /not marked as a global board/);
    assert.doesNotMatch(storedScopeText(null), /in-country|in country/);
  });

  it("reads scope from the URL and does not call a check a verification", () => {
    assert.equal(urlScopeText("https://board.myworkdayjobs.com/x?locationCountry=ZA").label, "Country filter");
    assert.match(checkedText("2026-10-12T08:00:00Z", true), /URL check on 2026-10-12/);
    assert.match(checkedText(null, null), /No URL check recorded yet/);
    assert.doesNotMatch(checkedText("2026-10-12T08:00:00Z", true), /verified/i);
  });

  it("lists employer pages in the sitemap and leaves them crawlable", () => {
    const sitemap = readFileSync(resolve(process.cwd(), "src/app/sitemap.ts"), "utf8");
    const robots = readFileSync(resolve(process.cwd(), "src/app/robots.ts"), "utf8");
    assert.match(sitemap, /\/employers\/ids/);
    assert.match(sitemap, /force-dynamic/);
    assert.match(sitemap, /unstable_cache/);
    assert.doesNotMatch(robots, /disallow: \[[^\]]*["']\/employers["']/s);
  });
});
