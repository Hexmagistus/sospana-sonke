/**
 * Build frontend/src/data/world-map.json from world-atlas (Natural Earth,
 * public domain). Not a runtime dependency.
 *
 *   mkdir -p /tmp/mapbuild && cd /tmp/mapbuild && npm init -y && npm install d3-geo@3 topojson-client@3
 *   MAP_DEPS=/tmp/mapbuild/package.json node frontend/scripts/build-world-map.mjs
 *
 * Antarctica is left out of the fit so the countries people can work in
 * stay large enough to read. Shapes are otherwise the Natural Earth
 * 1:110m countries, plus five small states the 110m set drops.
 */
import fs from "fs";
import { createRequire } from "node:module";

function loadDep(name) {
  const origins = [];
  if (process.env.MAP_DEPS) origins.push(process.env.MAP_DEPS);
  origins.push(new URL("../package.json", import.meta.url));
  const errors = [];
  for (const origin of origins) {
    try {
      return createRequire(origin)(name);
    } catch (err) {
      errors.push(err.message);
    }
  }
  throw new Error(`Cannot load ${name}. Set MAP_DEPS to a package.json that depends on it.\n${errors.join("\n")}`);
}

const { geoNaturalEarth1, geoPath } = loadDep("d3-geo");
const topojson = loadDep("topojson-client");

const ATLAS = "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2";
const OUT = new URL("../src/data/world-map.json", import.meta.url);

const DISPLAY = {
  "eSwatini": "Eswatini",
  "Dem. Rep. Congo": "DR Congo",
  "São Tomé and Principe": "Sao Tome and Principe",
  "Eq. Guinea": "Equatorial Guinea",
  "Central African Rep.": "Central African Republic",
  "S. Sudan": "South Sudan",
  "W. Sahara": "Western Sahara",
  "Bosnia and Herz.": "Bosnia and Herzegovina",
  "Dominican Rep.": "Dominican Republic",
  "United States of America": "United States",
  "Macedonia": "North Macedonia",
};

const EXTRA_FROM_50M = ["Mauritius", "Seychelles", "Comoros", "Cabo Verde", "São Tomé and Principe"];
const SKIP = new Set(["Antarctica", "Fr. S. Antarctic Lands"]);

function displayName(atlas) {
  return DISPLAY[atlas] || atlas;
}

function slug(name) {
  return name
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function roundPath(d) {
  return d.replace(/-?\d+\.\d+/g, (n) => String(Math.round(parseFloat(n) * 10) / 10));
}

function largestSubpath(d) {
  let best = 0;
  let cx = null;
  let cy = null;
  for (const part of d.split(/(?=M)/)) {
    const nums = part.match(/-?\d+\.?\d*/g);
    if (!nums || nums.length < 4) continue;
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    for (let i = 0; i < nums.length; i += 2) {
      const x = +nums[i];
      const y = +nums[i + 1];
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
    const span = Math.max(maxX - minX, maxY - minY);
    if (span > best) {
      best = span;
      cx = (minX + maxX) / 2;
      cy = (minY + maxY) / 2;
    }
  }
  return { span: best, cx, cy };
}

async function loadTopo(file) {
  const res = await fetch(`${ATLAS}/${file}`);
  if (!res.ok) throw new Error(`Failed to fetch ${file}: ${res.status}`);
  return res.json();
}

const [topo110, topo50] = await Promise.all([
  loadTopo("countries-110m.json"),
  loadTopo("countries-50m.json"),
]);
const fc110 = topojson.feature(topo110, topo110.objects.countries);
const fc50 = topojson.feature(topo50, topo50.objects.countries);
const features = [
  ...fc110.features.filter((f) => !SKIP.has(f.properties.name)),
  ...fc50.features.filter((f) => EXTRA_FROM_50M.includes(f.properties.name)),
];

const W = 960;
const H = 500;
const projection = geoNaturalEarth1().precision(0.4);
projection.fitExtent([[8, 12], [W - 8, H - 12]], { type: "FeatureCollection", features });
const path = geoPath(projection);

const countries = [];
for (const feature of features) {
  const atlas = feature.properties.name;
  const raw = path(feature);
  if (!raw) continue;
  const d = roundPath(raw);
  const local = largestSubpath(d);
  // Anchor on the largest piece of land. A centroid would sit in the
  // ocean for France (French Guiana) or a country split by the antimeridian.
  let x = local.cx;
  let y = local.cy;
  if (x == null || y == null) {
    const c = path.centroid(feature);
    x = c[0];
    y = c[1];
  }
  const item = {
    id: slug(displayName(atlas)),
    name: displayName(atlas),
    d,
    x: Math.round(x * 10) / 10,
    y: Math.round(y * 10) / 10,
  };
  // Islands and city-states disappear at world scale. A dot marks them.
  // Slightly larger countries (Lesotho, the Low Countries) keep their shape
  // so neighbouring pins do not pile on top of each other.
  if (local.span > 0 && local.span < 4.5) item.dot = true;
  countries.push(item);
}

const seen = new Map();
for (const country of countries) {
  const n = seen.get(country.id) || 0;
  seen.set(country.id, n + 1);
  if (n > 0) country.id = `${country.id}-${n + 1}`;
}

const page = fs.readFileSync(new URL("../src/app/page.tsx", import.meta.url), "utf8");
const liveBlock = page.split("const LIVE = [")[1].split("];")[0];
const liveNames = [...liveBlock.matchAll(/name: "([^"]+)"/g)].map((m) => m[1]);
const have = new Set(countries.map((c) => c.name));
const missing = liveNames.filter((name) => !have.has(name));
if (missing.length) {
  console.error("LIVE countries missing from the map:", missing.join(", "));
  process.exit(1);
}

const payload = { w: W, h: H, countries };
fs.mkdirSync(new URL("../src/data/", import.meta.url), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(payload));
const dots = countries.filter((c) => c.dot && liveNames.includes(c.name)).map((c) => c.name);
console.log(`wrote ${countries.length} countries, ${Buffer.byteLength(JSON.stringify(payload))} bytes`);
console.log("covered dots:", dots.sort().join(", "));
