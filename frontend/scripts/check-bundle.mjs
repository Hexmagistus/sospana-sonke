/**
 * Fail when the homepage first-load JavaScript printed by `next build`
 * is above the ceiling measured on 2026-10-13.
 *
 * The 2026-10-13 gate build printed `┌ ○ /  20 kB  154 kB`.
 * The soundtrack controls measured `┌ ○ /  20.4 kB  155 kB`.
 */
import { readFileSync } from "node:fs";

const ceilingKb = 155;
const logPath = process.argv[2];
if (!logPath) {
  console.error("usage: node scripts/check-bundle.mjs <next-build-log>");
  process.exit(2);
}

const log = readFileSync(logPath, "utf8");
const match = log.match(/^[┌├└]\s+[○ƒλ]\s+\/\s+[\d.]+\s*(?:kB|B)\s+([\d.]+)\s*kB\s*$/m);
if (!match) {
  console.error("Could not read the homepage First Load JS line from the build log.");
  process.exit(1);
}
const firstLoadKb = Number(match[1]);
console.log(`homepage first-load JS ${firstLoadKb} kB; ceiling ${ceilingKb} kB`);
if (firstLoadKb > ceilingKb) {
  console.error(`Homepage first-load JS ${firstLoadKb} kB is above ${ceilingKb} kB.`);
  process.exit(1);
}
