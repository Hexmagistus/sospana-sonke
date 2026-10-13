/**
 * Mobile Lighthouse on the homepage.
 * Three simulated-mobile runs. The median performance score must be at least 90.
 * Every accessibility score must be 100.
 * Best-practices is not gated: a localhost page calling Frankfurt records a
 * cross-origin console message that is not a product defect.
 */
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const url = process.env.LH_URL || "http://127.0.0.1:3000/";
const runs = 3;
const scores = [];

for (let i = 0; i < runs; i += 1) {
  const dir = mkdtempSync(join(tmpdir(), "lh-"));
  const out = join(dir, "report.json");
  const result = spawnSync(
    "npx",
    [
      "--yes",
      "lighthouse@12.8.2",
      url,
      "--only-categories=performance,accessibility",
      "--form-factor=mobile",
      "--screenEmulation.mobile",
      "--output=json",
      `--output-path=${out}`,
      "--quiet",
      "--chrome-flags=--headless=new --no-sandbox --disable-dev-shm-usage",
    ],
    { stdio: ["ignore", "inherit", "inherit"], env: process.env },
  );
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
  const report = JSON.parse(readFileSync(out, "utf8"));
  const performance = Math.round(report.categories.performance.score * 100);
  const accessibility = Math.round(report.categories.accessibility.score * 100);
  console.log(`run ${i + 1}: performance ${performance}, accessibility ${accessibility}`);
  scores.push({ performance, accessibility });
  rmSync(dir, { recursive: true, force: true });
}

const performance = scores.map((row) => row.performance).sort((a, b) => a - b);
const median = performance[Math.floor(performance.length / 2)];
const accessibility = Math.min(...scores.map((row) => row.accessibility));
console.log(`median performance ${median}; minimum accessibility ${accessibility}`);
if (median < 90 || accessibility < 100) {
  process.exit(1);
}
