import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it } from "node:test";
import { PUBLIC_LIST_SECONDS, PUBLIC_PAGE_SECONDS } from "./publicCache.js";

function source(path: string): string {
  return readFileSync(resolve(process.cwd(), path), "utf8");
}

describe("public page cache", () => {
  it("keeps the list window at 60 seconds and the slower pages at 300", () => {
    assert.equal(PUBLIC_LIST_SECONDS, 60);
    assert.equal(PUBLIC_PAGE_SECONDS, 300);
    const jobs = source("src/app/jobs/page.tsx");
    assert.match(jobs, /revalidate = 60/);
    assert.doesNotMatch(jobs, /force-dynamic/);
    assert.match(jobs, /revalidate: 60/);
    const data = source("src/app/data/page.tsx");
    assert.match(data, /revalidate = 300/);
    assert.doesNotMatch(data, /force-dynamic/);
    const config = source("next.config.mjs");
    assert.match(config, /s-maxage=60/);
    assert.match(config, /s-maxage=300/);
    assert.match(source("src/app/sitemap.ts"), /force-dynamic/);
  });
});