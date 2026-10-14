import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it } from "node:test";

function source(path: string): string {
  return readFileSync(resolve(process.cwd(), path), "utf8");
}

describe("expired opportunities stay off public pages", () => {
  it("search, programmes, feeds, sitemap and employer pages read the public job API", () => {
    assert.match(source("src/app/jobs/page.tsx"), /\/jobs\?/);
    assert.match(source("src/app/opportunities/page.tsx"), /\/jobs\?/);
    assert.match(source("src/app/feed.xml/route.ts"), /\/jobs\?limit=30/);
    assert.match(source("src/app/feed.json/route.ts"), /\/jobs\?limit=30/);
    assert.match(source("src/app/sitemap.ts"), /\/jobs\/ids/);
    assert.match(source("src/app/sitemap.ts"), /\/jobs\/counts/);
    assert.match(source("src/app/employers/[id]/page.tsx"), /\/employers\//);
  });

  it("a closed detail page is noindex and does not emit JobPosting", () => {
    const page = source("src/app/jobs/[id]/page.tsx");
    const closedAt = page.indexOf('job === "closed"');
    const schemaAt = page.indexOf("jobPosting(");
    assert.ok(closedAt > 0);
    assert.ok(schemaAt > closedAt);
    assert.match(page, /CLOSED_OPPORTUNITY_HEADING/);
    assert.match(page, /index: false/);
    assert.match(source("src/lib/loadPublicJob.ts"), /res\.status === 410/);
    assert.match(source("src/app/jobs/[id]/opengraph-image.tsx"), /CLOSED_OPPORTUNITY_HEADING/);
    assert.match(source("src/app/admin/page.tsx"), /\/admin\/vacancies\?status=/);
    assert.match(source("src/app/admin/page.tsx"), /private backup/);
    assert.match(source("src/app/privacy/page.tsx"), /An opportunity is deleted after/);
    assert.match(source("../docs/Sospana_Sonke_Legal_Pack.md"), /Expired opportunities are deleted/);
  });
});
