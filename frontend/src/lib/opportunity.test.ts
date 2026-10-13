import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { opportunityLabel, statedDate } from "./opportunity.js";

describe("opportunity labels", () => {
  it("names each stored type and leaves a missing date unstated", () => {
    assert.equal(opportunityLabel("learnership"), "Learnership");
    assert.equal(opportunityLabel("bursary"), "Bursary");
    assert.equal(opportunityLabel("graduate_programme"), "Graduate programme");
    assert.equal(opportunityLabel("internship"), "Internship");
    assert.equal(opportunityLabel(null), "Job");
    assert.equal(statedDate(null), "not stated");
    assert.equal(statedDate("2026-11-02T00:00:00Z"), "2026-11-02");
  });
});
