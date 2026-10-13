import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { jobPosting, jobSummary, type PublicJob } from "./jobPosting.js";

function job(overrides: Partial<PublicJob> = {}): PublicJob {
  return {
    id: "v1",
    title: "Operations Manager",
    company_name: "Acme Mines",
    company_country: "South Africa",
    location: "Johannesburg",
    country: null,
    employment_type: null,
    work_mode: null,
    salary: null,
    salary_min: null,
    salary_max: null,
    salary_currency: null,
    posting_date: null,
    closing_date: null,
    first_seen_at: "2026-10-11T08:00:00Z",
    last_seen_at: "2026-10-11T08:00:00Z",
    application_url: "https://example.com/jobs/ops",
    is_open: true,
    ...overrides,
  };
}

describe("public job posting schema", () => {
  it("uses only stored fields and falls back to the day the scanner first saw the role", () => {
    const node = jobPosting(job());
    assert.equal(node["@type"], "JobPosting");
    assert.equal(node.title, "Operations Manager");
    assert.equal(node.datePosted, "2026-10-11");
    assert.equal(node.url, "https://sospana-sonke.vercel.app/jobs/v1");
    assert.equal(node.directApply, false);
    assert.equal("baseSalary" in node, false);
    assert.equal("validThrough" in node, false);
    assert.match(jobSummary(job()), /Operations Manager at Acme Mines/);
    assert.match(jobSummary(job()), /Johannesburg/);
    assert.doesNotMatch(jobSummary(job()), /remote/i);
  });

  it("includes pay and a closing date only when the source has them", () => {
    const node = jobPosting(job({
      salary: "R20,000 a month",
      salary_min: 20000,
      salary_currency: "ZAR",
      closing_date: "2026-10-30",
      posting_date: "2026-10-01",
      employment_type: "Permanent",
    }));
    assert.equal(node.datePosted, "2026-10-01");
    assert.equal(node.validThrough, "2026-10-30");
    assert.equal(node.employmentType, "FULL_TIME");
    const salary = node.baseSalary as { currency: string; value: { minValue: number } };
    assert.equal(salary.currency, "ZAR");
    assert.equal(salary.value.minValue, 20000);
    assert.match(String(node.description), /R20,000 a month/);
  });
});
