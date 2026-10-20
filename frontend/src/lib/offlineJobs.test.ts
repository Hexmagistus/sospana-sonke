import { test } from "node:test";
import assert from "node:assert/strict";
import { isBootstrapJob, offlineBanner, parseSaved, saToday, unexpiredJobs } from "./offlineJobs.js";

test("expired roles are never kept", () => {
  const jobs = [
    { id: "a", closing_date: "2026-10-19" },
    { id: "b", closing_date: "2026-10-20" },
    { id: "c", closing_date: null },
    { id: "d", closing_date: "2027-01-01", is_open: false },
  ];
  assert.deepEqual(unexpiredJobs(jobs, "2026-10-20").map((j) => j.id), ["b", "c"]);
});

test("SA day rolls over at 22:00 UTC", () => {
  assert.equal(saToday(new Date("2026-10-20T21:59:00Z")), "2026-10-20");
  assert.equal(saToday(new Date("2026-10-20T22:01:00Z")), "2026-10-21");
});

test("banner names the saved date", () => {
  assert.match(offlineBanner("2026-10-20T06:00:00Z"), /^Offline – showing jobs saved on 20 Oct 2026$/);
});

test("parseSaved rejects junk", () => {
  assert.equal(parseSaved("nope"), null);
  assert.equal(parseSaved(JSON.stringify({ jobs: [] })), null);
  assert.equal(parseSaved(JSON.stringify({ savedAt: "x", jobs: [] }))?.savedAt, "x");
  assert.equal(isBootstrapJob("bootstrap-atns"), true);
});
