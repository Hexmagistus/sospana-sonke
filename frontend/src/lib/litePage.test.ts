import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  blocksHeavyMedia,
  liteDocument,
  liteEmployerPage,
  liteJobPage,
  liteProgrammesPage,
  liteSearchPage,
  safeReturnPath,
  shouldSuggestLite,
  type LiteJob,
} from "./litePage.js";

const job: LiteJob = {
  id: "f2a26f43-00fa-4791-a16e-717c99af6c29",
  title: "Senior Provisioning Officer",
  company_name: "Example Employer",
  company_id: "d723ab63-2511-4e1d-bdf8-7db9293d0c34",
  company_country: "South Africa",
  location: "Johannesburg",
  closing_date: "2026-10-28",
  application_url: "https://careers.example/jobs/1",
};

function assertTextOnly(html: string) {
  assert.equal(/<script/i.test(html), false);
  assert.equal(/<img/i.test(html), false);
  assert.equal(/<audio/i.test(html), false);
  assert.equal(/<video/i.test(html), false);
  assert.equal(/<canvas/i.test(html), false);
  assert.equal(/ambient\.ogg/i.test(html), false);
  assert.equal(/webgl/i.test(html), false);
  assert.ok(html.length < 50 * 1024, `page is ${html.length} bytes`);
}

describe("lite pages", () => {
  it("blocks 3D and music on lite, Save-Data, and the data-saver switch", () => {
    assert.equal(blocksHeavyMedia(false, null, false), false);
    assert.equal(blocksHeavyMedia(true, "0", false), true);
    assert.equal(blocksHeavyMedia(false, "1", false), true);
    assert.equal(blocksHeavyMedia(false, "0", true), true);
  });

  it("keeps search, programmes, employers and a role under 50 KB with no script or media", () => {
    const jobs = Array.from({ length: 8 }, (_, index) => ({
      ...job,
      id: `00000000-0000-4000-8000-${String(index).padStart(12, "0")}`,
      title: "A".repeat(140),
    }));
    const pages = [
      liteSearchPage({ q: "nurse", country: undefined, jobs, matched: 3200, offset: 0 }),
      liteProgrammesPage({ type: "learnership", jobs, matched: 40 }),
      liteEmployerPage({
        id: job.company_id || "",
        name: "Example Employer",
        country: "South Africa",
        careersUrl: "https://careers.example/jobs",
        openCount: 12,
        roles: jobs,
      }),
      liteJobPage(job),
      liteDocument("Empty", "<p>Nothing stored.</p>"),
    ];
    for (const html of pages) assertTextOnly(html);
    assert.match(liteSearchPage({ q: "", country: undefined, jobs, matched: 1, offset: 0 }), /South Africa/);
    assert.match(liteJobPage(job), /careers\.example/);
    assert.match(liteJobPage({ ...job, title: "<script>" }), /&lt;script&gt;/);
  });

  it("suggests lite on Save-Data and refuses an off-site return path", () => {
    assert.equal(shouldSuggestLite("on", undefined), true);
    assert.equal(shouldSuggestLite("on", "full"), false);
    assert.equal(shouldSuggestLite(null, "lite"), true);
    assert.equal(shouldSuggestLite(null, undefined), false);
    assert.equal(safeReturnPath("/jobs?q=nurse"), "/jobs?q=nurse");
    assert.equal(safeReturnPath("https://evil.example"), "/");
    assert.equal(safeReturnPath("//evil.example"), "/");
  });
});
