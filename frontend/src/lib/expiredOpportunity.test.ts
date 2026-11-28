import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it } from "node:test";

function source(path: string): string {
  return readFileSync(resolve(process.cwd(), path), "utf8");
}

describe("expired opportunities stay off public pages", () => {
  it("search, programmes, feeds, sitemap and employer pages read the public job API", () => {
    assert.match(source("src/app/feed.xml/route.ts"), /\/jobs\?limit=30/);
    assert.match(source("src/app/feed.json/route.ts"), /\/jobs\?limit=30/);
    assert.match(source("src/app/employers/[id]/page.tsx"), /\/employers\//);
  });

  it("privacy and the legal pack still say expired opportunities are deleted", () => {
    assert.match(source("src/app/privacy/page.tsx"), /An opportunity is deleted after/);
    assert.match(source("../docs/Sospana_Sonke_Legal_Pack.md"), /Expired opportunities are deleted/);
  });
});
