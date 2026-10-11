import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { linkScope } from "./linkScope.js";

describe("careers link scope", () => {
  it("reads a Workday country filter from either query key", () => {
    const lower = linkScope("https://analogdevices.wd1.myworkdayjobs.com/External?locationCountry=bc33aa3152ec42d4995f4791a106ed09");
    const upper = linkScope("https://aviva.wd1.myworkdayjobs.com/External?Location_Country=29247e57dbaf46fb855b224e03170bc7");
    assert.equal(lower.kind, "country");
    assert.equal(upper.kind, "country");
    assert.equal(lower.label, "Country filter");
  });

  it("does not treat an empty country parameter as a filter", () => {
    const scope = linkScope("https://example.wd1.myworkdayjobs.com/External?locationCountry=");
    assert.equal(scope.kind, "unfiltered");
  });

  it("calls an unfiltered applicant-system board unfiltered, not global", () => {
    const scope = linkScope("https://boards.greenhouse.io/example");
    assert.equal(scope.kind, "unfiltered");
    assert.equal(scope.label, "No country filter");
    assert.match(scope.detail, /not limited to one country/);
  });

  it("keeps an employer's own site separate from a job board", () => {
    assert.equal(linkScope("https://www.eskom.co.za/careers").kind, "own");
    assert.equal(linkScope("https://www.pnet.co.za/jobs").kind, "board");
    assert.equal(linkScope("https://www.indeed.com/cmp/example").kind, "board");
  });

  it("says when there is no link", () => {
    assert.equal(linkScope("").kind, "none");
    assert.equal(linkScope(null).kind, "none");
    assert.equal(linkScope("not a url").kind, "none");
  });
});
