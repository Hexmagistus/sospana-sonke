/* ============================================================
   GAUTENG HUSTLE RUN  (formerly Bond Village Hustle)
   Endless runner through the whole of Gauteng: Soweto, Joburg CBD,
   Alexandra, Sandton, Rosebank, Midrand, Pretoria, Mamelodi,
   Kempton Park, Ekurhuleni, the West Rand and the Vaal.
   Vanilla JS + Canvas2D. No external dependencies.

   v3.2 "Gauteng Edition": three difficulty levels (EASY / NORMAL / DIFFICULT, one DIFFICULTY table), offline PWA (sw.js + pwa.js).
   v3.1 "Gauteng Edition": 34 areas in 5 regions on a fixed geographic route (a unique WebP plate each), a run cycle that is
   stride-synced to the ground, jump phases, walk-cycle pedestrians, kids with a real ball arc.
   v3.0 "Gauteng Edition": 14 areas with painted plates, palettes, landmarks
   and street signs; three playable characters (GUPTA, BIZA, LEBZA) with
   character select; illustrated sprite heroes + township people.
   v2.1 "GUPTA Edition": triple jump, skateboard, toy blaster, the
   Sospana Sonke shop (+2 lives), brighter look, rolling credits.
   v2.0 "Kasi Edition": procedural township scenery, combo / near-miss,
   Quantum Taxi, banners and stage-transition effects.

   Art: hero/people sprites + the new Gauteng plates are generated
   illustrations (assets/hero/<id>, assets/people, assets/backgrounds).
   BIZA uses the original hero PNGs (assets/hero/idle_*, run_*, jump).
   Everything else (taxis, houses, poles, props) is drawn in code.
   ============================================================ */
(function () {
"use strict";

const GAME_VERSION = "3.2 Gauteng Edition";
// GUPTA / LEBZA use illustrated sprite sets; if a set fails to load the procedural cartoon (GuptaArt) is used instead.
const USE_CARTOON_GUPTA = true;   // = allow the procedural fallback
// Animals-on-the-road hazards (dogs). Off by default: the road hazards are now obstacles + rolling tyres only.
const ROAD_DOGS = false;
const AUTO_FIRE = true;              // blaster fires by itself at obstacles ahead (you can also tap FIRE / press F)
const WIN_DISTANCE = 1500;           // reaching this distance before game over rolls the credits automatically

/* ---------------------------------------------------------
   CONSTANTS
--------------------------------------------------------- */
// Logical canvas resolution — CH is fixed (keeps physics/jump-arc tuning
// consistent), CW adapts to the device's actual aspect ratio so the game
// fills the entire screen edge-to-edge on any phone/tablet, landscape,
// instead of being letterboxed to a fixed 16:9 box.
let CH = 540;
let CW = 960;
const CH_BASE = 540;                     // reference height all tuning below is designed around
const GROUND_Y_RATIO = 430 / 540;
let GROUND_Y = Math.round(CH * GROUND_Y_RATIO);
const PLAYER_X_RATIO = 175 / 960;
let PLAYER_X = Math.round(CW * PLAYER_X_RATIO);
const GRAVITY = 2500;
const JUMP_VELOCITY = -880;
const PLAYER_W = 70, PLAYER_H = 108;
const START_LIVES = 4;                   // (legacy constant - the real value now comes from the DIFFICULTY table)
const MAX_LIVES = 10;                    // cap raised so the Sospana Sonke shop (+2) always fits
const DAY_CYCLE_LENGTH = 95;             // seconds for a full day/night cycle

/* ---------------------------------------------------------
   DIFFICULTY  (v3.2)  -  ALL the tuning lives in this one table.
   EASY   = the relaxed v3.1 feel, a little more forgiving.
   NORMAL = moderate: fewer lives, faster ramp and cap, closer gaps, extra obstacles.
   DIFFICULT = hard: 2 lives, fast ramp / high cap, tight gaps, double obstacles,
               smaller rewards, rarer power-ups and shops - but score x1.5.
   speed:   px/s = start + clamp(dist*gain, 0, ramp) + min(late, max(0, dist-1400)*0.02)   (cap = start+ramp+late)
   tiers:   distances (m) where the obstacle mix gets harder (tier 1,2,3)
   gapMul:  multiplies the pixel gap between obstacle groups (smaller = closer)
   doubleChance: chance that a single obstacle is followed by a second one
   hitW/hitH:    player hitbox as a fraction of the sprite box (smaller = more forgiving)
   collect: chance of a coin/pick-up burst instead of an obstacle [tier 0, later tiers]
   cashMul / scoreMul: pick-up reward size / final score multiplier
   nearMiss: max clearance (px) that still counts as a near miss
   powerupMul: multiplies the time between power-up spawns (bigger = rarer)
   shopFirst / shopEvery: metres until the first Sospana Sonke shop / between shops
   heartKeep: chance that a heart pick-up is allowed to spawn when you are below your starting lives
   rescue: a skateboard turns up when you are on your last life
--------------------------------------------------------- */
const DIFFICULTY = {
  easy: {
    key: "easy", label: "EASY", color: "#5fd16a", blurb: "5 lives · relaxed speed · long grace time · forgiving hitboxes",
    lives: 5, invuln: 3.2, hitW: 0.36, hitH: 0.64,
    speed: { start: 215, gain: 0.12, ramp: 170, late: 20 }, tiers: [200, 500, 1000], gapMul: 1.1, doubleChance: 0,
    collect: [0.52, 0.60], cashMul: 1.25, scoreMul: 1, nearMiss: 60, powerupMul: 0.85, shopFirst: 300, shopEvery: 700, heartKeep: 1, rescue: true
  },
  normal: {
    key: "normal", label: "NORMAL", color: "#ffd23f", blurb: "3 lives · quicker ramp · closer gaps · more obstacles",
    lives: 3, invuln: 1.8, hitW: 0.46, hitH: 0.74,
    speed: { start: 235, gain: 0.20, ramp: 260, late: 40 }, tiers: [120, 350, 700], gapMul: 0.88, doubleChance: 0.10,
    collect: [0.46, 0.54], cashMul: 1, scoreMul: 1, nearMiss: 50, powerupMul: 1, shopFirst: 450, shopEvery: 850, heartKeep: 0.8, rescue: true
  },
  difficult: {
    key: "difficult", label: "DIFFICULT", color: "#ff5252", blurb: "2 lives · fast & relentless · tight gaps · rare shops · score x1.5",
    lives: 2, invuln: 1.2, hitW: 0.52, hitH: 0.80,
    speed: { start: 260, gain: 0.28, ramp: 380, late: 60 }, tiers: [60, 200, 450], gapMul: 0.75, doubleChance: 0.28,
    collect: [0.38, 0.46], cashMul: 0.6, scoreMul: 1.5, nearMiss: 34, powerupMul: 1.7, shopFirst: 1000, shopEvery: 1000, heartKeep: 0.4, rescue: false
  }
};
const DIFF_ORDER = ["easy", "normal", "difficult"];
const DIFF_STORE = "ghr_diff";
let DIFF_KEY = "normal";                                   // default level
try { const s = localStorage.getItem(DIFF_STORE); if (s && DIFFICULTY[s]) DIFF_KEY = s; } catch (e) {}
function DIFF() { return DIFFICULTY[DIFF_KEY]; }
function readBest(level) {                                 // best scores are kept separately for every level
  const g = (k) => { try { return parseInt(localStorage.getItem(k) || "0", 10) || 0; } catch (e) { return 0; } };
  let dist = g("bvh_best_dist_" + level), cash = g("bvh_best_cash_" + level);
  if (level === "easy") { dist = Math.max(dist, g("bvh_best_dist")); cash = Math.max(cash, g("bvh_best_cash")); }   // pre-v3.2 records were set on the relaxed tuning
  return { dist, cash };
}
function writeBest(level, b) { try { localStorage.setItem("bvh_best_dist_" + level, String(b.dist)); localStorage.setItem("bvh_best_cash_" + level, String(b.cash)); } catch (e) {} }

// Recompute CW/CH/derived layout constants for the current window size.
// Called on load, resize, and orientation change.
function computeResponsiveDimensions() {
  const vw = window.innerWidth, vh = window.innerHeight;
  const aspect = clamp(vw / vh, 1.25, 2.3); // clamp to sane landscape range
  CH = CH_BASE;
  CW = Math.round(CH * aspect);
  GROUND_Y = Math.round(CH * GROUND_Y_RATIO);
  PLAYER_X = Math.round(CW * PLAYER_X_RATIO);
}

/* ---------------------------------------------------------
   THE GAUTENG JOURNEY  (v3.1)
   34 areas across the 5 regions (Sedibeng/Vaal, City of Johannesburg,
   Tshwane, Ekurhuleni, West Rand), each with its OWN painted plate.
   Lap 1 is a fixed geographic route: Vaal/Emfuleni home first, then
   Johannesburg south -> north, Tshwane, Ekurhuleni, West Rand.
   Only after every area has been shown does the route loop: the order is
   reshuffled (seeded, never the same plate twice in a row) and re-tinted.
   Plates are WebP, LAZY-LOADED (current + next only, older ones released).
--------------------------------------------------------- */
const PLATE_DIR = "assets/backgrounds/";
const REGIONS = ["Sedibeng · Vaal", "City of Johannesburg", "Tshwane", "Ekurhuleni", "West Rand"];
// [file id, area name, sub-line, [street names], Town palette, metres, region index]
const AREA_DATA = [
  ["vaal_evaton",   "Evaton",            "Emfuleni · Vaal",                 ["Old Evaton Road", "Golden Highway"],            0, 300, 0],
  ["sebokeng",      "Sebokeng",          "Emfuleni · Vaal",                 ["Houtkop Road", "Golden Highway"],               13, 290, 0],
  ["sharpeville",   "Sharpeville",       "Emfuleni · Human Rights Precinct", ["Seeiso Street", "Sharpeville Road"],           0, 280, 0],
  ["vanderbijlpark","Vanderbijlpark",    "Emfuleni · Steel City",           ["Frikkie Meyer Boulevard", "Hendrik van Eck Boulevard"], 2, 320, 0],
  ["vereeniging",   "Vereeniging",       "Emfuleni · Vaal Barrage",         ["Barrage Road", "Voortrekker Street"],            2, 340, 0],
  ["kliptown",      "Kliptown",          "Soweto · Walter Sisulu Square",   ["Union Road", "Klipspruit Valley Road"],          1, 290, 1],
  ["soweto",        "Soweto",            "Orlando West · Vilakazi Street",  ["Vilakazi Street", "Mooki Street", "Chris Hani Road"], 1, 380, 1],
  ["diepkloof",     "Diepkloof",         "Soweto · Jacaranda streets",      ["Old Potchefstroom Road", "Chris Hani Road"],     1, 290, 1],
  ["newtown",       "Newtown",           "Johannesburg · Mandela Bridge",   ["Miriam Makeba Street", "Henry Nxumalo Street"],  3, 300, 1],
  ["joburg_cbd",    "Joburg CBD",        "Johannesburg · Ponte & Carlton",  ["Bree Street", "Eloff Street", "Jeppe Street"],   3, 380, 1],
  ["maboneng",      "Maboneng",          "Johannesburg · Arts precinct",    ["Fox Street", "Kruger Street"],                   3, 280, 1],
  ["hillbrow",      "Hillbrow",          "Johannesburg · Telkom Tower",     ["Kotze Street", "Pretoria Street"],               3, 300, 1],
  ["alexandra",     "Alexandra",         "Johannesburg · Alex",             ["2nd Avenue", "London Road"],                     4, 320, 1],
  ["rosebank",      "Rosebank",          "Johannesburg North",              ["Oxford Road", "Jan Smuts Avenue"],               6, 320, 1],
  ["sandton",       "Sandton",           "Nelson Mandela Square",           ["Rivonia Road", "Maude Street", "Sandton Drive"], 5, 380, 1],
  ["fourways",      "Fourways",          "Johannesburg · Northern suburbs", ["William Nicol Drive", "Witkoppen Road"],          5, 290, 1],
  ["midrand",       "Midrand",           "Halfway House · Gautrain",        ["Allandale Road", "New Road"],                    7, 330, 1],
  ["centurion",     "Centurion",         "Tshwane · Centurion Lake",        ["Jean Avenue", "Lenchen Avenue"],                 7, 300, 2],
  ["pretoria",      "Pretoria",          "Tshwane · Union Buildings",       ["Madiba Street", "Paul Kruger Street"],           8, 380, 2],
  ["church_square", "Church Square",     "Tshwane · Pretoria CBD",          ["Church Street", "Lilian Ngoyi Street"],          8, 290, 2],
  ["hatfield",      "Hatfield",          "Tshwane · Campus & cafés",        ["Burnett Street", "Duncan Street"],               8, 290, 2],
  ["atteridgeville","Atteridgeville",    "Tshwane · West",                  ["Church Street West"],                            9, 270, 2],
  ["mamelodi",      "Mamelodi",          "Tshwane · East",                  ["Tsamaya Road", "Solomon Mahlangu Drive"],        9, 330, 2],
  ["soshanguve",    "Soshanguve",        "Tshwane · North",                 ["Mabopane Highway"],                              9, 270, 2],
  ["kempton_park",  "Kempton Park",      "Ekurhuleni · OR Tambo",           ["Monument Road", "Pretoria Road"],               10, 320, 3],
  ["tembisa",       "Tembisa",           "Ekurhuleni · North",              ["Andrew Mapheto Drive", "Winnie Mandela Drive"], 11, 320, 3],
  ["ekurhuleni",    "Germiston",         "Ekurhuleni · Rail & gold",        ["Voortrekker Road", "President Street"],         11, 330, 3],
  ["boksburg",      "Boksburg",          "Ekurhuleni · East Rand",          ["North Rand Road", "Commissioner Street"],       10, 290, 3],
  ["springs",       "Springs",           "Ekurhuleni · East Rand",          ["Main Reef Road"],                               11, 270, 3],
  ["katlehong",     "Katlehong",         "Ekurhuleni · South",              ["Khumalo Street"],                               11, 270, 3],
  ["roodepoort",    "Roodepoort",        "West Rand · Johannesburg West",   ["Ontdekkers Road", "Hendrik Potgieter Road"],    12, 320, 4],
  ["krugersdorp",   "Krugersdorp",       "West Rand · Mogale City",         ["Commissioner Street", "Paardekraal Avenue"],    12, 310, 4],
  ["west_rand",     "Cradle of Humankind","West Rand · Magaliesburg hills", ["Kromdraai Road"],                               12, 340, 4],
  ["carletonville", "Carletonville",     "West Rand · Gold-mining belt",    ["Annan Road", "Van Zyl Street"],                 12, 280, 4]
];
const AREAS = AREA_DATA.map((r, i) => ({ index: i, id: r[0], key: "bg_" + r[0], file: r[0] + ".webp", fileFallback: r[0] + ".png", name: r[1], region: r[2], streets: r[3], pal: r[4], len: r[5], regionIdx: r[6] }));
const AREA_BY_KEY = {};
AREAS.forEach((a) => { AREA_BY_KEY[a.key] = a; });

// The journey is an endless list of "slots" {start, len, area, lap, pos}. Lap 0 follows AREAS order
// (the fixed geographic route). Laps >= 1 reshuffle with a seeded RNG; the first plate of a lap
// is never the last plate of the previous one, so two consecutive plates are never identical.
const Journey = (function () {
  const slots = [], orders = [];
  let endD = 0;
  function mulberry(a) { return function () { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  function orderFor(lap) {
    if (orders[lap]) return orders[lap];
    const n = AREAS.length;
    let o = AREAS.map((_, i) => i);
    if (lap > 0) {
      const prevLast = orderFor(lap - 1)[n - 1], rnd = mulberry(0x9e3779b1 ^ (lap * 7919));
      for (let i = n - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); const t = o[i]; o[i] = o[j]; o[j] = t; }
      if (o[0] === prevLast) { const j = 1 + Math.floor(rnd() * (n - 1)); const t = o[0]; o[0] = o[j]; o[j] = t; }
      if (o[0] === prevLast) { const t = o[0]; o[0] = o[1]; o[1] = t; }
    }
    return (orders[lap] = o);
  }
  function extend(d) {
    while (endD <= d) {
      const n = slots.length, lap = Math.floor(n / AREAS.length), pos = n % AREAS.length;
      const a = AREAS[orderFor(lap)[pos]];
      slots.push({ n, start: endD, len: a.len, area: a, lap, pos });
      endD += a.len;
    }
  }
  function slotAt(d) {
    d = Math.max(0, d); extend(d);
    let lo = 0, hi = slots.length - 1;
    while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (slots[mid].start <= d) lo = mid; else hi = mid - 1; }
    return slots[lo];
  }
  function slot(n) { extend(0); while (slots.length <= n) extend(endD); return slots[n]; }
  function startOfSlot(n) { return slot(n).start; }
  return { slotAt, slot, startOfSlot, orderFor, total: () => AREAS.reduce((s, a) => s + a.len, 0) };
})();
function areaAt(d) { return Journey.slotAt(d).area; }
function areaIndexAt(d) { return Journey.slotAt(d).n; }                 // unbounded slot counter
function areaStart(i) { return Journey.startOfSlot(i); }                // i = slot number
function streetIndexAt(d) {
  const s = Journey.slotAt(d), n = s.area.streets.length;
  return Math.min(n - 1, Math.floor((d - s.start) / s.len * n));
}

// Plate loader: WebP first, PNG fallback (old WebViews without WebP), current + next only.
const PlateStore = {
  loading: {},
  ensure(key) {
    if (IMAGES[key] && IMAGES[key].width) return Promise.resolve(IMAGES[key]);
    if (this.loading[key]) return this.loading[key];
    const a = AREA_BY_KEY[key]; if (!a) return Promise.resolve(null);
    const p = loadImage(PLATE_DIR + a.file)
      .then((img) => (img && img.width) ? img : loadImage(PLATE_DIR + a.fileFallback))
      .then((img) => { delete this.loading[key]; if (img && img.width) IMAGES[key] = img; return img; });
    return (this.loading[key] = p);
  },
  keep(keys) { for (const k of Object.keys(IMAGES)) if (k.indexOf("bg_") === 0 && keys.indexOf(k) < 0) delete IMAGES[k]; },
  loaded() { return Object.keys(IMAGES).filter(k => k.indexOf("bg_") === 0); }
};

// A blue street-name sign on a pole that scrolls past on the pavement ("Vilakazi Street" / "SOWETO").
const BG_TINTS = [
  { color: "rgba(255,170,80,0.13)", op: "overlay" },     // warm late-afternoon
  { color: "rgba(110,165,255,0.12)", op: "overlay" },    // cool morning
  { color: "rgba(255,120,175,0.10)", op: "overlay" },    // rose
  { color: "rgba(110,225,160,0.09)", op: "overlay" }     // fresh green
];
class AreaSign {
  constructor(x, street, area) { this.x = x; this.street = street; this.area = area; this.span = 0; this.h = 118; }
  update(dt, speed) { this.x -= speed * dt; }
  draw(ctx) {
    const x = this.x, base = GROUND_Y - 4, top = base - this.h;
    if (x < -140 || x > CW + 140) return;
    ctx.save();
    ctx.fillStyle = "rgba(0,0,0,0.2)"; ctx.beginPath(); ctx.ellipse(x, base + 2, 12, 3, 0, 0, 6.3); ctx.fill();
    ctx.fillStyle = "#6b7078"; ctx.fillRect(x - 2.5, top + 20, 5, this.h - 20);
    ctx.fillStyle = "#9aa0a8"; ctx.fillRect(x - 2.5, top + 20, 1.8, this.h - 20);
    const txt = this.street.toUpperCase();
    ctx.font = "900 15px 'Segoe UI', Arial, sans-serif";
    const w = Math.max(116, Math.ceil(ctx.measureText(txt).width) + 26), h = 34;
    ctx.fillStyle = "#08306b"; ctx.beginPath(); ctx.roundRect(x - w / 2, top, w, h, 6); ctx.fill();
    ctx.lineWidth = 2.5; ctx.strokeStyle = "#ffffff"; ctx.beginPath(); ctx.roundRect(x - w / 2 + 3, top + 3, w - 6, h - 6, 4); ctx.stroke();
    ctx.fillStyle = "#fff"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(txt, x, top + h / 2 + 0.5);
    ctx.font = "800 10px 'Segoe UI', Arial, sans-serif";
    const w2 = Math.max(70, Math.ceil(ctx.measureText(this.area.name.toUpperCase()).width) + 18);
    ctx.fillStyle = "#0b6e3a"; ctx.beginPath(); ctx.roundRect(x - w2 / 2, top + h + 3, w2, 17, 4); ctx.fill();
    ctx.fillStyle = "#ffe9a8"; ctx.fillText(this.area.name.toUpperCase(), x, top + h + 12);
    ctx.restore();
  }
}

/* ---------------------------------------------------------
   ASSET MANIFEST (every path below was individually eyeballed
   against the source sheet — see header comment)
--------------------------------------------------------- */
const MANIFEST = {
  hero_idle_right: "assets/hero/idle_right.png",
  hero_idle_left: "assets/hero/idle_left.png",
  hero_run_right: ["assets/hero/run_right/1.png","assets/hero/run_right/2.png","assets/hero/run_right/3.png","assets/hero/run_right/4.png","assets/hero/run_right/5.png"],
  hero_run_left: ["assets/hero/run_left/1.png","assets/hero/run_left/2.png","assets/hero/run_left/3.png","assets/hero/run_left/4.png","assets/hero/run_left/5.png"],
  hero_jump: ["assets/hero/jump/1.png","assets/hero/jump/2.png","assets/hero/jump/3.png","assets/hero/jump/4.png"],

  // (painted background plates are lazy-loaded per area - see PlateStore)
  // township people (generated illustrations, cut out)
  ppl_kid_kick: "assets/people/kid_kick.png", ppl_kid_dribble: "assets/people/kid_dribble.png",
  ppl_hawker_stall: "assets/people/hawker_stall.png", ppl_vendor_crate: "assets/people/vendor_crate.png",
  ppl_braai_man: "assets/people/braai_man.png", ppl_shop_owner: "assets/people/shop_owner.png",
  ppl_spaza_keeper: "assets/people/spaza_keeper.png", ppl_commuter_woman: "assets/people/commuter_woman.png",
  ppl_ball: "assets/people/ball.png",

  // collectibles (coins/gems/moneybag/star/heart)
  coin_spin: ["assets/collectibles/coin_a.png","assets/collectibles/coin_b.png","assets/collectibles/coin_c.png","assets/collectibles/coin_d.png"],
  gem_green: "assets/collectibles/gem_green.png",
  gem_red: "assets/collectibles/gem_red.png",
  gem_blue: "assets/collectibles/gem_blue.png",
  gem_purple: "assets/collectibles/gem_purple.png",
  gem_rainbow: "assets/collectibles/gem_rainbow.png",
  moneybag: "assets/collectibles/moneybag.png",
  star: "assets/collectibles/star.png",
  heart: "assets/collectibles/heart.png",

  // ground obstacles
  ob_crate: "assets/obstacles/crate.png",
  ob_barrel: "assets/obstacles/barrel.png",
  ob_rock1: "assets/obstacles/rock1.png",
  ob_rock2: "assets/obstacles/rock2.png",
  ob_rock3: "assets/obstacles/rock3.png",
  ob_rockpile: "assets/obstacles/rockpile.png",
  ob_spikes: "assets/obstacles/spikes.png",
  ob_pot: "assets/obstacles/pot.png",

  // roadside decor (non-colliding)
  dc_bush: "assets/decor/bush.png",
  dc_tree: "assets/decor/tree.png",
  dc_fence: "assets/decor/fence.png",
  dc_signpost: "assets/decor/signpost.png"
};

// walk-cycle frames for the pavement walkers (see WALK_META)
{
  const WM = {"schoolboy": {"w": 96, "h": 148, "ax": 42, "n": 5, "spread": [88, 32, 32, 83, 37], "refH": 144}, "schoolgirl": {"w": 96, "h": 147, "ax": 41, "n": 5, "spread": [84, 43, 37, 88, 38], "refH": 142}, "businessman": {"w": 94, "h": 160, "ax": 41, "n": 6, "spread": [85, 78, 29, 85, 81, 76], "refH": 158}, "woman_bag": {"w": 112, "h": 161, "ax": 51, "n": 6, "spread": [102, 52, 78, 99, 65, 96], "refH": 158}, "elder": {"w": 92, "h": 163, "ax": 46, "n": 6, "spread": [79, 83, 63, 82, 80, 60], "refH": 159}, "hoodie": {"w": 105, "h": 166, "ax": 49, "n": 6, "spread": [88, 93, 68, 91, 97, 79], "refH": 162}};
  for (const n of Object.keys(WM)) for (let i = 1; i <= WM[n].n; i++) MANIFEST["ppl_walk_" + n + "_" + i] = "assets/people/walk_" + n + "_" + i + ".png";
}

const IMAGES = {};

function loadImage(src) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => resolve(img); // fail-soft: don't block the game on one bad asset
    img.src = src;
  });
}

async function loadAllAssets(onProgress) {
  const keys = Object.keys(MANIFEST);
  let total = 0, loaded = 0;
  keys.forEach(k => total += Array.isArray(MANIFEST[k]) ? MANIFEST[k].length : 1);

  for (const key of keys) {
    const entry = MANIFEST[key];
    if (Array.isArray(entry)) {
      IMAGES[key] = [];
      for (const src of entry) {
        const img = await loadImage(src);
        IMAGES[key].push(img);
        loaded++; onProgress(loaded / total);
      }
    } else {
      IMAGES[key] = await loadImage(entry);
      loaded++; onProgress(loaded / total);
    }
  }
}

/* ---------------------------------------------------------
   AUDIO ENGINE (procedurally synthesized — no external files)
--------------------------------------------------------- */
const Audio_ = (function () {
  let ctx = null;
  let muted = false;
  try { muted = localStorage.getItem("bvh_muted") === "1"; } catch (e) {}

  function ensureCtx() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) ctx = new AC();
    }
    if (ctx && ctx.state === "suspended") ctx.resume();
    return ctx;
  }

  function tone(freq, dur, type, gainVal, when, slideTo) {
    if (muted) return;
    const c = ensureCtx();
    if (!c) return;
    const t0 = c.currentTime + (when || 0);
    const osc = c.createOscillator();
    const gain = c.createGain();
    osc.type = type || "square";
    osc.frequency.setValueAtTime(freq, t0);
    if (slideTo) osc.frequency.linearRampToValueAtTime(slideTo, t0 + dur);
    gain.gain.setValueAtTime(0.0001, t0);
    gain.gain.exponentialRampToValueAtTime(gainVal || 0.15, t0 + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    osc.connect(gain).connect(c.destination);
    osc.start(t0);
    osc.stop(t0 + dur + 0.02);
  }

  function noise(dur, gainVal, when) {
    if (muted) return;
    const c = ensureCtx();
    if (!c) return;
    const t0 = c.currentTime + (when || 0);
    const bufferSize = c.sampleRate * dur;
    const buffer = c.createBuffer(1, bufferSize, c.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / bufferSize);
    const src = c.createBufferSource();
    src.buffer = buffer;
    const gain = c.createGain();
    gain.gain.setValueAtTime(gainVal || 0.2, t0);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    src.connect(gain).connect(c.destination);
    src.start(t0);
  }

  return {
    jump(n) { n = n || 0; const f = 440 * (1 + 0.2 * n); tone(f, 0.14, "square", 0.12, 0, f * 1.68); },
    zap() { tone(1250, 0.1, "square", 0.07, 0, 420); tone(1700, 0.05, "sine", 0.05, 0.02, 900); },
    shop() { [523, 659, 784, 1046, 1318].forEach((f, i) => tone(f, 0.16, "triangle", 0.12, i * 0.09)); tone(1568, 0.5, "sine", 0.1, 0.5); },
    board() { tone(330, 0.12, "square", 0.09, 0, 660); tone(660, 0.18, "square", 0.09, 0.1, 990); noise(0.2, 0.08, 0.05); },
    coin() { tone(920, 0.09, "square", 0.10, 0, 1400); tone(1400, 0.07, "square", 0.08, 0.05); },
    gem() { tone(700,0.08,"sine",0.12,0,1100); tone(1100,0.08,"sine",0.1,0.07,1500); tone(1500,0.1,"sine",0.1,0.14,1900); },
    bigCash() { tone(500,0.09,"square",0.13,0,760); tone(760,0.09,"square",0.12,0.08,1000); tone(1000,0.12,"square",0.12,0.16,1300); },
    heartPickup() { tone(600,0.12,"sine",0.14,0,900); tone(900,0.14,"sine",0.12,0.1,1200); },
    hit() { noise(0.25, 0.3); tone(140, 0.2, "sawtooth", 0.15, 0, 60); },
    lifeLost() { tone(300, 0.35, "sawtooth", 0.15, 0, 90); },
    gameOver() { tone(300, 0.18, "sawtooth", 0.16, 0, 220); tone(220, 0.18, "sawtooth", 0.16, 0.18, 140); tone(140, 0.3, "sawtooth", 0.16, 0.36, 70); },
    click() { tone(600, 0.06, "square", 0.08, 0, 800); },
    honk() { tone(300, 0.2, "sawtooth", 0.14, 0, 260); tone(220, 0.22, "sawtooth", 0.14, 0.12, 200); },
    bark() { noise(0.08, 0.18); tone(180, 0.08, "square", 0.1, 0); },
    powerup() { tone(500, 0.1, "sine", 0.14, 0, 900); tone(900, 0.12, "sine", 0.12, 0.09, 1300); },
    zone() { tone(660, 0.12, "sine", 0.1, 0, 990); tone(990, 0.14, "sine", 0.1, 0.1, 1320); },
    milestone() { tone(523,0.1,"sine",0.12,0,659); tone(659,0.1,"sine",0.12,0.1,784); tone(784,0.18,"sine",0.14,0.2,1046); },
    combo(level) { const b = 520 + level * 60; tone(b, 0.08, "square", 0.08, 0, b * 1.25); tone(b * 1.25, 0.08, "square", 0.08, 0.07, b * 1.5); tone(b * 1.5, 0.12, "square", 0.08, 0.14, b * 2); },
    whoosh() { noise(0.18, 0.12); tone(300, 0.16, "sine", 0.07, 0, 900); },
    smash() { noise(0.12, 0.2); tone(220, 0.1, "square", 0.1, 0, 90); },
    stage() { tone(220, 0.5, "sawtooth", 0.07, 0, 880); noise(0.4, 0.1); tone(660, 0.15, "sine", 0.1, 0.3, 990); tone(990, 0.2, "sine", 0.1, 0.42, 1320); },
    taxiRide() { tone(392, 0.14, "square", 0.1, 0); tone(392, 0.14, "square", 0.1, 0.18); tone(523, 0.3, "square", 0.1, 0.36, 560); },
    setMuted(v) { muted = v; try { localStorage.setItem("bvh_muted", v ? "1" : "0"); } catch (e) {} },
    isMuted() { return muted; },
    unlock() { ensureCtx(); }
  };
})();

/* ---------------------------------------------------------
   INPUT — jump only. No lane switching.
--------------------------------------------------------- */
const Input = { listeners: [] };

function fireAction(action) {
  Input.listeners.forEach(fn => fn(action));
}

function setupInput(canvas) {
  window.addEventListener("keydown", (e) => {
    if (e.code === "Space") { e.preventDefault(); if (!e.repeat) fireAction("jumpDown"); }
    else if (e.key === "ArrowUp") { if (!e.repeat) fireAction("jumpDown"); }
    else if (e.key === "Escape" || e.key === "p" || e.key === "P") fireAction("pause");
    else if ((e.code === "KeyF" || e.code === "KeyX") && !e.repeat) fireAction("fire");
    else if ((e.code === "Enter" || e.code === "KeyE") && !e.repeat) fireAction("enter");
  });
  window.addEventListener("keyup", (e) => {
    if (e.code === "Space" || e.key === "ArrowUp") fireAction("jumpUp");
  });

  canvas.addEventListener("touchstart", (e) => { e.preventDefault(); fireAction("jumpDown"); }, { passive: false });
  canvas.addEventListener("touchend", (e) => { e.preventDefault(); fireAction("jumpUp"); }, { passive: false });
  canvas.addEventListener("mousedown", () => fireAction("jumpDown"));
  window.addEventListener("mouseup", () => fireAction("jumpUp"));

  Input.on = (fn) => Input.listeners.push(fn);
}

/* ---------------------------------------------------------
   UTILITY
--------------------------------------------------------- */
function rand(a, b) { return a + Math.random() * (b - a); }
function randInt(a, b) { return Math.floor(rand(a, b + 1)); }
function pick(arr) { return arr[randInt(0, arr.length - 1)]; }
function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
function lerp(a, b, t) { return a + (b - a) * t; }
function aabbOverlap(a, b) {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}

/* ---------------------------------------------------------
   PLAYER — fixed single lane, constant size (no scaling, ever)
--------------------------------------------------------- */
/* ---------------------------------------------------------
   GUPTA — the hero, drawn procedurally as a polished cartoon.
   Side-view character with a big expressive head, outlined shapes,
   shading + highlights, township clothing (green cap, yellow "43"
   tee, jeans, sneakers). Legs/arms use two-bone IK so the run, jump,
   idle, hurt, skate and shoot poses all stay anatomically believable.
   Faces both directions (st.facing = 1 / -1).
   The original sprite PNGs stay as an automatic fallback (see
   USE_CARTOON_GUPTA at the top of this file).
--------------------------------------------------------- */
const GuptaArt = (function () {
  const OUT = "#2a1810";
  const SKIN = "#a2663f", SKIN_D = "#7d4a2d", SKIN_L = "#c38558";
  const JEANS = "#3b72bd", JEANS_D = "#2a5594";
  const TEE = "#ffb703", TEE_D = "#e08a00";
  const CAP = "#1fa35c", CAP_D = "#15794a", BRIM = "#ffd23f";

  function ik(ox, oy, tx, ty, l1, l2, dir) {
    let dx = tx - ox, dy = ty - oy, d = Math.hypot(dx, dy);
    const max = (l1 + l2) * 0.999;
    if (d > max) { tx = ox + dx / d * max; ty = oy + dy / d * max; dx = tx - ox; dy = ty - oy; d = max; }
    if (d < 1) d = 1;
    const base = Math.atan2(dy, dx);
    const c = Math.max(-1, Math.min(1, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)));
    const a = base + dir * Math.acos(c);
    return { kx: ox + Math.cos(a) * l1, ky: oy + Math.sin(a) * l1, fx: tx, fy: ty };
  }
  function limb(g, ox, oy, J, w, col, hi) {
    g.lineCap = "round"; g.lineJoin = "round";
    g.beginPath(); g.moveTo(ox, oy); g.lineTo(J.kx, J.ky); g.lineTo(J.fx, J.fy);
    g.strokeStyle = OUT; g.lineWidth = w + 3.6; g.stroke();
    g.strokeStyle = col; g.lineWidth = w; g.stroke();
    if (hi) { g.strokeStyle = hi; g.lineWidth = w * 0.28; g.beginPath(); g.moveTo(ox - w * 0.2, oy); g.lineTo(J.kx - w * 0.2, J.ky); g.lineTo(J.fx - w * 0.2, J.fy); g.stroke(); }
  }
  function shoe(g, fx, fy, tilt) {
    g.save(); g.translate(fx, fy); g.rotate(tilt || 0);
    g.beginPath();
    g.moveTo(-6.5, -4); g.lineTo(2.5, -4); g.bezierCurveTo(6, -1, 10.5, 0, 13, 2.4); g.lineTo(13.4, 5); g.lineTo(-7, 5); g.closePath();
    g.fillStyle = "#fbfbfb"; g.fill(); g.lineWidth = 2.2; g.strokeStyle = OUT; g.lineJoin = "round"; g.stroke();
    g.fillStyle = "#e63946"; g.beginPath(); g.moveTo(8, 0.2); g.bezierCurveTo(10.5, 0.6, 12, 1.4, 13, 2.6); g.lineTo(13.2, 4.6); g.lineTo(7, 4.6); g.closePath(); g.fill();
    g.fillStyle = "#d8dde3"; g.fillRect(-7, 3.2, 20.4, 1.9);
    g.strokeStyle = "#e63946"; g.lineWidth = 1.4; g.beginPath(); g.moveTo(-3, -1); g.lineTo(3.5, 2.4); g.stroke();
    g.fillStyle = "rgba(255,255,255,0.9)"; g.fillRect(-4.6, -3, 3.6, 1.2);
    g.restore();
  }
  function hand(g, x, y) {
    g.beginPath(); g.arc(x, y, 4.9, 0, Math.PI * 2); g.fillStyle = SKIN; g.fill();
    g.lineWidth = 2; g.strokeStyle = OUT; g.stroke();
    g.fillStyle = "rgba(255,255,255,0.22)"; g.beginPath(); g.arc(x - 1.4, y - 1.6, 1.6, 0, Math.PI * 2); g.fill();
  }
  function star(g, x, y, r1, r2, n, rot) {
    g.beginPath();
    for (let i = 0; i < n * 2; i++) { const a = rot + i * Math.PI / n, r = i % 2 ? r2 : r1; g.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r); }
    g.closePath();
  }
  // Toy-style pulse blaster (bright, cartoon, no realism)
  function blaster(g, x, y, rot, flash) {
    g.save(); g.translate(x, y); g.rotate(rot);
    g.lineJoin = "round"; g.lineWidth = 2.2; g.strokeStyle = OUT;
    // handle
    g.fillStyle = "#ff5fa2"; g.beginPath(); g.moveTo(-4, 2); g.lineTo(3, 2); g.lineTo(5, 13); g.lineTo(-3, 13); g.closePath(); g.fill(); g.stroke();
    // body
    g.fillStyle = "#2ec4b6"; g.beginPath(); g.roundRect ? g.roundRect(-9, -7, 26, 11, 4) : g.rect(-9, -7, 26, 11); g.fill(); g.stroke();
    g.fillStyle = "rgba(255,255,255,0.45)"; g.fillRect(-6, -5.4, 18, 2.2);
    // barrel tip + ring
    g.fillStyle = "#ff9f1c"; g.beginPath(); g.roundRect ? g.roundRect(16, -6, 9, 9, 3) : g.rect(16, -6, 9, 9); g.fill(); g.stroke();
    g.fillStyle = "#ffe14d"; star(g, 3, -1.5, 3.4, 1.5, 5, -Math.PI / 2); g.fill();
    g.fillStyle = "#e63946"; g.beginPath(); g.arc(-4, -9.2, 2, 0, Math.PI * 2); g.fill(); g.stroke();
    if (flash > 0) {
      const r = 6 + flash * 9;
      g.fillStyle = "rgba(255,255,255,0.95)"; star(g, 29, -1.5, r, r * 0.38, 7, flash * 2); g.fill();
      g.fillStyle = "rgba(255,210,70,0.9)"; star(g, 29, -1.5, r * 0.62, r * 0.25, 7, -flash * 2); g.fill();
    }
    g.restore();
  }

  function face(g, hx, hy, mood, blink, t) {
    // cheek blush
    g.fillStyle = "rgba(255,110,90,0.28)"; g.beginPath(); g.ellipse(hx + 9, hy + 8, 4.4, 2.8, 0, 0, Math.PI * 2); g.fill();
    // eyes
    const eyes = [hx + 5.5, hx + 15];
    if (mood === "hurt") {
      g.strokeStyle = OUT; g.lineWidth = 2.4; g.lineCap = "round";
      eyes.forEach(ex => { g.beginPath(); g.moveTo(ex - 3.4, hy - 2.6); g.lineTo(ex + 2.6, hy + 1); g.lineTo(ex - 3.4, hy + 4.6); g.stroke(); });
    } else if (blink) {
      g.strokeStyle = OUT; g.lineWidth = 2.2; g.lineCap = "round";
      eyes.forEach(ex => { g.beginPath(); g.arc(ex, hy + 1.5, 3.6, 0.15 * Math.PI, 0.85 * Math.PI); g.stroke(); });
    } else {
      eyes.forEach((ex, i) => {
        const squint = mood === "aim" && i === 1;
        g.fillStyle = "#fff"; g.beginPath(); g.ellipse(ex, hy + 1.6, 4.3, squint ? 2.2 : 5.3, 0, 0, Math.PI * 2); g.fill();
        g.lineWidth = 1.5; g.strokeStyle = OUT; g.stroke();
        g.fillStyle = "#1b0f0a"; g.beginPath(); g.ellipse(ex + 1.5, hy + 2.2, 2.7, squint ? 1.6 : 3.1, 0, 0, Math.PI * 2); g.fill();
        g.fillStyle = "#fff"; g.beginPath(); g.arc(ex + 0.6, hy + 0.7, 1.05, 0, Math.PI * 2); g.fill();
      });
    }
    // eyebrows (expression)
    let tilt = 1.6, lift = 0;
    if (mood === "jump") { tilt = -1.6; lift = -2.2; }
    else if (mood === "hurt") { tilt = -2.4; lift = -1.2; }
    else if (mood === "idle") { tilt = -0.2; lift = 0; }
    else if (mood === "aim") { tilt = 2.6; lift = 0.4; }
    g.strokeStyle = "#1b0f0a"; g.lineWidth = 2.6; g.lineCap = "round";
    [[hx + 1.6, hx + 9], [hx + 11.2, hx + 18.6]].forEach(([a, b], i) => {
      g.beginPath(); g.moveTo(a, hy - 6.6 + lift + (i ? -tilt * 0.5 : tilt * 0.3)); g.lineTo(b, hy - 6.6 + lift + (i ? tilt * 0.3 : -tilt * 0.5)); g.stroke();
    });
    // nose
    g.strokeStyle = SKIN_D; g.lineWidth = 2; g.beginPath(); g.moveTo(hx + 19.4, hy + 3.6); g.quadraticCurveTo(hx + 22.5, hy + 6.4, hx + 19.2, hy + 8); g.stroke();
    // mouth
    const mx = hx + 12.5, my = hy + 12.6;
    if (mood === "jump" || mood === "run" || mood === "board") {
      g.fillStyle = "#6b1620"; g.beginPath(); g.moveTo(mx - 5, my - 1.2); g.quadraticCurveTo(mx, my + 7.5, mx + 5.6, my - 1.2); g.closePath(); g.fill();
      g.fillStyle = "#fff"; g.fillRect(mx - 3.8, my - 1.2, 8, 2.2);
      g.lineWidth = 1.8; g.strokeStyle = OUT; g.beginPath(); g.moveTo(mx - 5, my - 1.2); g.quadraticCurveTo(mx, my + 7.5, mx + 5.6, my - 1.2); g.closePath(); g.stroke();
    } else if (mood === "hurt") {
      g.strokeStyle = OUT; g.lineWidth = 2.2; g.beginPath(); g.moveTo(mx - 5, my + 2); g.quadraticCurveTo(mx - 2.5, my - 1, mx, my + 2); g.quadraticCurveTo(mx + 2.5, my + 5, mx + 5, my + 2); g.stroke();
    } else if (mood === "aim") {
      g.strokeStyle = OUT; g.lineWidth = 2.2; g.beginPath(); g.moveTo(mx - 5, my + 0.6); g.quadraticCurveTo(mx + 1, my + 4.4, mx + 6.4, my - 1.6); g.stroke();
    } else {
      g.strokeStyle = OUT; g.lineWidth = 2.2; g.beginPath(); g.moveTo(mx - 5, my); g.quadraticCurveTo(mx, my + 4.6, mx + 5.4, my - 0.4); g.stroke();
    }
  }

  function head(g, hx, hy, mood, blink, t) {
    // back hair tuft (under cap)
    g.fillStyle = "#1b0f0a";
    [[-17, 2, 5.4], [-18.4, 8, 5], [-15, 13, 4.6]].forEach(([dx, dy, r]) => { g.beginPath(); g.arc(hx + dx, hy + dy, r, 0, Math.PI * 2); g.fill(); });
    // ear
    g.beginPath(); g.arc(hx - 10, hy + 3.6, 4.5, 0, Math.PI * 2); g.fillStyle = SKIN_D; g.fill(); g.lineWidth = 2; g.strokeStyle = OUT; g.stroke();
    // head
    const gr = g.createRadialGradient(hx - 5, hy - 6, 3, hx, hy, 24);
    gr.addColorStop(0, SKIN_L); gr.addColorStop(0.55, SKIN); gr.addColorStop(1, SKIN_D);
    g.beginPath(); g.ellipse(hx, hy, 19.5, 19, 0, 0, Math.PI * 2); g.fillStyle = gr; g.fill();
    g.lineWidth = 2.6; g.strokeStyle = OUT; g.stroke();
    face(g, hx, hy, mood, blink, t);
    // cap dome
    g.beginPath(); g.ellipse(hx, hy - 1.4, 20.6, 19.4, 0, Math.PI * 1.02, Math.PI * 1.98);
    g.quadraticCurveTo(hx + 8, hy - 7.5, hx - 20.2, hy - 4.6); g.closePath();
    g.fillStyle = CAP; g.fill(); g.lineWidth = 2.6; g.strokeStyle = OUT; g.stroke();
    g.fillStyle = CAP_D; g.beginPath(); g.ellipse(hx, hy - 1.4, 20.6, 19.4, 0, Math.PI * 1.55, Math.PI * 1.98); g.quadraticCurveTo(hx + 12, hy - 8.5, hx + 3, hy - 9); g.closePath(); g.fill();
    g.strokeStyle = "rgba(0,0,0,0.3)"; g.lineWidth = 1.3; g.beginPath(); g.moveTo(hx + 2, hy - 20); g.quadraticCurveTo(hx + 6, hy - 14, hx + 4, hy - 7.6); g.stroke();
    g.fillStyle = "rgba(255,255,255,0.4)"; g.beginPath(); g.ellipse(hx - 7, hy - 14.2, 6.4, 2.6, -0.5, 0, Math.PI * 2); g.fill();
    g.fillStyle = BRIM; g.beginPath(); g.arc(hx + 2, hy - 20, 2.4, 0, Math.PI * 2); g.fill(); g.lineWidth = 1.4; g.strokeStyle = OUT; g.stroke();
    // brim
    g.beginPath(); g.moveTo(hx + 10, hy - 8); g.quadraticCurveTo(hx + 28, hy - 10, hx + 36, hy - 3.4); g.quadraticCurveTo(hx + 30, hy + 1.2, hx + 11, hy - 3.2); g.closePath();
    g.fillStyle = BRIM; g.fill(); g.lineWidth = 2.2; g.strokeStyle = OUT; g.stroke();
    g.fillStyle = "rgba(0,0,0,0.18)"; g.beginPath(); g.moveTo(hx + 12, hy - 4); g.quadraticCurveTo(hx + 28, hy - 3.4, hx + 34, hy - 3.6); g.quadraticCurveTo(hx + 30, hy + 0.6, hx + 12, hy - 3.2); g.closePath(); g.fill();
    // cap badge: little gold star
    g.fillStyle = "#ffe14d"; star(g, hx + 10, hy - 13, 3.8, 1.7, 5, -Math.PI / 2); g.fill(); g.lineWidth = 1; g.strokeStyle = OUT; g.stroke();
    // head highlight
    g.fillStyle = "rgba(255,255,255,0.18)"; g.beginPath(); g.ellipse(hx - 9, hy + 5, 3.2, 5.2, 0.3, 0, Math.PI * 2); g.fill();
  }

  function torso(g, hipY, shY) {
    const top = shY - 3, bot = hipY + 4;
    g.beginPath();
    g.moveTo(-12.5, top + 3); g.quadraticCurveTo(-13, top, -9, top); g.lineTo(9, top); g.quadraticCurveTo(13, top, 12.6, top + 4);
    g.lineTo(11, bot); g.quadraticCurveTo(0, bot + 3, -11.5, bot); g.closePath();
    const gr = g.createLinearGradient(-12, 0, 12, 0); gr.addColorStop(0, "#ffc933"); gr.addColorStop(0.6, TEE); gr.addColorStop(1, TEE_D);
    g.fillStyle = gr; g.fill(); g.lineWidth = 2.6; g.strokeStyle = OUT; g.lineJoin = "round"; g.stroke();
    // collar
    g.strokeStyle = "rgba(0,0,0,0.35)"; g.lineWidth = 2; g.beginPath(); g.arc(1, top + 0.5, 6, 0.15 * Math.PI, 0.85 * Math.PI); g.stroke();
    // belt + hem
    g.fillStyle = "#3a2a1c"; g.fillRect(-11.5, bot - 3.2, 23, 3.2);
    g.fillStyle = "#ffe14d"; g.fillRect(-1.6, bot - 3.2, 3.2, 3.2);
    // print "43"
    g.fillStyle = "#1fa35c"; g.font = "900 11px 'Segoe UI', Arial, sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
    g.fillText("43", 0.5, (top + bot) / 2 - 0.5);
    g.fillStyle = "rgba(255,255,255,0.28)"; g.fillRect(-9, top + 3, 2.4, (bot - top) * 0.55);
  }

  function draw(ctx, st) {
    const t = st.t || 0, state = st.state || "idle";
    const facing = st.facing || 1;
    const sc = st.scale || 0.95;
    const g = ctx;
    g.save();
    g.translate(st.x, st.y);
    if (st.alpha !== undefined) g.globalAlpha *= st.alpha;
    const sq = st.squash || 0;
    g.scale(sc * (1 + sq * 0.12) * facing, sc * (1 - sq * 0.12));
    if (st.flip) { g.translate(0, -52); g.rotate(st.flip * Math.PI * 2); g.translate(0, 52); }
    if (st.hurtShake) g.translate(Math.sin(t * 70) * 2, 0);

    // ---- pose
    let hipH = 40, bob = 0, lean = 0, mood = state;
    let F = [{ x: 6, y: -4, tilt: 0 }, { x: -6, y: -4, tilt: 0 }];   // feet targets (ground coords)
    let Hh = null;                                                      // hand targets (relative to shoulder, in body frame)
    const ph = t * 12;
    if (state === "run") {
      bob = Math.abs(Math.sin(ph)) * 3;
      for (let i = 0; i < 2; i++) {
        const p = ph + i * Math.PI, lift = Math.max(0, -Math.sin(p)) * 15;
        F[i] = { x: 17 * Math.cos(p) + 2, y: -4 - lift, tilt: lift > 3 ? (Math.cos(p) > 0 ? -0.2 : 0.35) : 0 };
      }
      Hh = [{ x: 14 * Math.cos(ph + Math.PI) + 4, y: 17 - Math.max(0, -Math.sin(ph + Math.PI)) * 9 }, { x: 14 * Math.cos(ph) + 4, y: 17 - Math.max(0, -Math.sin(ph)) * 9 }];
      lean = 0.14;
    } else if (state === "jump") {
      const k = Math.max(0, Math.min(1, 0.5 + (st.vy || 0) / 700));
      F[0] = { x: lerp(17, 8, k), y: lerp(-26, -7, k), tilt: lerp(0.3, 0.1, k) };
      F[1] = { x: lerp(-13, -6, k), y: lerp(-14, -5, k), tilt: lerp(0.5, 0.2, k) };
      Hh = [{ x: lerp(14, 17, k), y: lerp(-8, 9, k) }, { x: lerp(-8, -15, k), y: lerp(-6, 8, k) }];
      lean = lerp(0.18, 0.02, k); hipH = 38;
    } else if (state === "hurt") {
      F[0] = { x: 12, y: -4, tilt: 0 }; F[1] = { x: -12, y: -9, tilt: 0.3 };
      Hh = [{ x: 15, y: -14 }, { x: -13, y: -16 }];
      lean = -0.25; hipH = 38;
    } else if (state === "board") {
      F[0] = { x: 11, y: -12, tilt: 0 }; F[1] = { x: -11, y: -12, tilt: 0 }; hipH = 33;
      bob = Math.sin(t * 6) * 0.8;
      Hh = [{ x: 19, y: 8 }, { x: -17, y: 4 }];
      lean = 0.2;
    } else {   // idle
      bob = Math.sin(t * 2.2) * 0.9; hipH = 41;
      const tap = Math.max(0, Math.sin(t * 5)) * (Math.floor(t / 2) % 3 === 0 ? 3.5 : 0);
      F[0] = { x: 7, y: -4 - tap, tilt: 0 }; F[1] = { x: -6, y: -4, tilt: 0 };
      Hh = [{ x: 5 + Math.sin(t * 2.2) * 1.5, y: 25 }, { x: -5, y: 25 }];
      mood = "idle";
    }
    // gun: near arm points the blaster forward
    const gun = !!st.gun;
    const shoot = st.shoot || 0;
    if (gun) { Hh[0] = { x: 24 - shoot * 5, y: 1 - shoot * 3 }; if (state === "run" || state === "idle") mood = "aim"; }
    if (state === "board" && !gun) mood = "board";

    const hipY = -(hipH + bob);
    const shY = hipY - 30;

    // ---- shadow + board (board sits under the feet)
    if (state === "board") {
      g.save();
      g.lineJoin = "round";
      g.beginPath(); g.moveTo(-30, -15); g.quadraticCurveTo(-27, -7, -22, -6.4); g.lineTo(22, -6.4); g.quadraticCurveTo(27, -7, 30, -15);
      g.lineTo(31.5, -14.6); g.quadraticCurveTo(29, -3.6, 22, -3.4); g.lineTo(-22, -3.4); g.quadraticCurveTo(-29, -3.6, -31.5, -14.6); g.closePath();
      g.fillStyle = "#ff6b35"; g.fill(); g.lineWidth = 2.4; g.strokeStyle = OUT; g.stroke();
      g.fillStyle = "#ffe14d"; g.fillRect(-18, -6, 36, 1.8);
      g.fillStyle = "#222"; g.fillRect(-14, -9.6, 3, 3.2); g.fillRect(11, -9.6, 3, 3.2);
      [-17, 17].forEach(wx => {
        g.beginPath(); g.arc(wx, -2.4, 4.4, 0, Math.PI * 2); g.fillStyle = "#f4f4f4"; g.fill(); g.lineWidth = 2; g.strokeStyle = OUT; g.stroke();
        g.strokeStyle = "#666"; g.lineWidth = 1.2; g.beginPath(); g.moveTo(wx + Math.cos(t * 22) * 3, -2.4 + Math.sin(t * 22) * 3); g.lineTo(wx - Math.cos(t * 22) * 3, -2.4 - Math.sin(t * 22) * 3); g.stroke();
      });
      g.restore();
    }

    // ---- legs (IK, knees forward). far leg = index 1
    const hipX = [-1.5, 1.5];
    const legs = [];
    for (let i = 0; i < 2; i++) legs[i] = ik(hipX[i], hipY, F[i].x, F[i].y - 0, 21.5, 21.5, -1);
    const shoulder = { x: 1, y: shY };
    function drawLeg(i, shade) {
      const J = legs[i];
      limb(g, hipX[i], hipY, J, 11.5, shade ? JEANS_D : JEANS, shade ? null : "rgba(255,255,255,0.16)");
      // jeans cuff
      g.strokeStyle = shade ? "#1f4175" : "#2a5594"; g.lineWidth = 3; g.lineCap = "butt";
      const ang = Math.atan2(J.fy - J.ky, J.fx - J.kx);
      g.beginPath(); g.moveTo(J.fx - Math.cos(ang) * 5.5 + Math.sin(ang) * 6, J.fy - Math.sin(ang) * 5.5 - Math.cos(ang) * 6); g.lineTo(J.fx - Math.cos(ang) * 5.5 - Math.sin(ang) * 6, J.fy - Math.sin(ang) * 5.5 + Math.cos(ang) * 6); g.stroke();
      shoe(g, J.fx, J.fy, F[i].tilt);
    }
    // ground shadow
    if (!st.noShadow) { g.fillStyle = "rgba(0,0,0,0.22)"; g.beginPath(); g.ellipse(2, 1, 24, 4.5, 0, 0, Math.PI * 2); g.fill(); }
    drawLeg(1, true);

    // upper body in a leaned frame
    g.save();
    g.translate(0, hipY); g.rotate(lean * (state === "hurt" ? 1 : 1)); g.translate(0, -hipY);
    // far arm (index 1)
    const sleeveCol = TEE;
    const arms = [];
    for (let i = 0; i < 2; i++) arms[i] = ik(shoulder.x, shoulder.y, shoulder.x + Hh[i].x, shoulder.y + Hh[i].y, 14, 13.5, +1);
    limb(g, shoulder.x, shoulder.y, arms[1], 8, SKIN_D);
    hand(g, arms[1].fx, arms[1].fy);
    // neck + torso
    g.fillStyle = SKIN_D; g.fillRect(-3.5, shY - 9, 8, 8);
    torso(g, hipY, shY);
    g.restore();

    drawLeg(0, false);

    g.save();
    g.translate(0, hipY); g.rotate(lean); g.translate(0, -hipY);
    // head
    const blink = (state === "idle" || state === "run") && (t % 3.4) < 0.13;
    head(g, 3.5, shY - 21, mood, blink, t);
    // near arm (+ sleeve) and blaster
    limb(g, shoulder.x, shoulder.y, arms[0], 8, SKIN, "rgba(255,255,255,0.14)");
    // sleeve on the upper arm
    g.strokeStyle = OUT; g.lineWidth = 11.4; g.lineCap = "round";
    const sx = shoulder.x + (arms[0].kx - shoulder.x) * 0.5, sy = shoulder.y + (arms[0].ky - shoulder.y) * 0.5;
    g.beginPath(); g.moveTo(shoulder.x, shoulder.y); g.lineTo(sx, sy); g.stroke();
    g.strokeStyle = TEE; g.lineWidth = 8.2; g.beginPath(); g.moveTo(shoulder.x, shoulder.y); g.lineTo(sx, sy); g.stroke();
    if (gun) blaster(g, arms[0].fx + 1, arms[0].fy - 1, -0.05 - shoot * 0.22, shoot > 0.45 ? shoot : 0);
    hand(g, arms[0].fx, arms[0].fy);
    g.restore();

    // dizzy stars when hurt
    if (state === "hurt") {
      for (let i = 0; i < 3; i++) {
        const a = t * 7 + i * 2.1;
        g.fillStyle = "#ffe14d"; star(g, 4 + Math.cos(a) * 20, shY - 46 + Math.sin(a) * 5, 4.4, 1.9, 5, a); g.fill();
        g.lineWidth = 1; g.strokeStyle = OUT; g.stroke();
      }
    }
    g.restore();
  }

  // Render a standalone portrait to a canvas -> data URL (used by the menu)
  function portrait(w, h, st) {
    const c = document.createElement("canvas"); c.width = w; c.height = h;
    const g = c.getContext("2d");
    const s = Object.assign({ x: w / 2 - 4, y: h - 10, scale: (h - 18) / 118, state: "idle", t: 0.4, facing: 1, noShadow: false }, st || {});
    draw(g, s);
    return c.toDataURL("image/png");
  }
  return { draw, portrait };
})();

/* ---------------------------------------------------------
   PLAYABLE CHARACTERS
   GUPTA and LEBZA are illustrated sprite sets (assets/hero/<id>/*.png,
   13 frames each, anchored on the feet). BIZA is the original hero:
   it uses the original hero PNGs through the legacy sprite path.
   If a sprite set fails to load, GUPTA / LEBZA fall back to the
   procedural GuptaArt cartoon, so the game always has a hero.
--------------------------------------------------------- */
const HERO_DS = 0.49;                // sprite pixels -> game pixels (idle ≈ 113 px tall)
const SHEET_FRAMES = ["idle","jump_up","jump_fall","hurt","aim","hold","board","crouch","tuck"];   // + the run-cycle frames listed in meta.run
const RUNMETA = {"gupta":{"run":["run01","run02","run03","run04","run05","run06","run07","run08","run09","run10"],"runT":[0.0,0.0713,0.1814,0.2901,0.3648,0.4792,0.6243,0.7233,0.8156,0.9154],"stepPx":96,"fist":{"run01":[141.4,113.8],"run02":[145.0,113.9],"run03":[141.1,117.7],"run04":[141.2,114.0],"run05":[139.2,116.3],"run06":[140.5,114.3],"run07":[145.1,105.3],"run08":[140.6,111.7],"run09":[143.3,99.9],"run10":[142.8,106.2],"crouch":[143.6,129.6],"tuck":[139.9,135.5]}},"lebza":{"run":["run01","run02","run03","run04","run05","run06","run07","run08","run09"],"runT":[0.0,0.0687,0.1479,0.2441,0.3762,0.5709,0.7272,0.8577,0.9323],"stepPx":85,"fist":{"run01":[131.9,123.9],"run02":[129.8,123.5],"run03":[132.3,124.6],"run04":[131.9,119.2],"run05":[129.9,121.2],"run06":[131.6,124.1],"run07":[130.1,125.0],"run08":[130.0,124.0],"run09":[130.5,127.1],"crouch":[129.0,154.0],"tuck":[127.7,152.0]}}};
const CHARACTERS = {
  gupta: { id: "gupta", name: "GUPTA", kind: "sheet", dir: "assets/hero/gupta/", portrait: "assets/hero/gupta/idle.png",
           tag: "Cap on · No. 43", color: "#ffd23f", meta: {"w":190,"h":253,"ax":95,"ay":249,"fist":{"idle":[120,136],"jump_up":[136,139],"jump_fall":[138,174],"run1":[148,115],"run2":[150,118],"run3":[152,118],"run4":[149,115],"run5":[150,116],"run6":[151,119],"board":[162,156],"hold":[137,155]},"tip":[153,99]} },
  biza:  { id: "biza", name: "BIZA", kind: "legacy", portrait: "assets/hero/idle_right.png",
           tag: "The original hustler", color: "#ff9f1c" },
  lebza: { id: "lebza", name: "LEBZA", kind: "sheet", dir: "assets/hero/lebza/", portrait: "assets/hero/lebza/idle.png",
           tag: "Jozi's fastest girl", color: "#ff5fa2", meta: {"w":184,"h":252,"ax":92,"ay":248,"fist":{"idle":[122,136],"jump_up":[133,135],"jump_fall":[135,171],"run1":[139,117],"run2":[140,122],"run3":[139,128],"run4":[139,119],"run5":[140,120],"run6":[140,120],"board":[154,158],"hold":[133,157]},"tip":[146,103]} }
};
// merge the v3.1 run-cycle data (frame list, stride-synced frame times, step length, blaster grip per frame)
for (const id of ["gupta", "lebza"]) { const m = CHARACTERS[id].meta, r = RUNMETA[id]; m.run = r.run; m.runT = r.runT; m.stepPx = r.stepPx; Object.assign(m.fist, r.fist); }
const CHAR_ORDER = ["gupta", "biza", "lebza"];
const CHAR_KEY = "ghr_char";
let CURRENT_CHAR = "gupta";
try { const s = localStorage.getItem(CHAR_KEY); if (s && CHARACTERS[s]) CURRENT_CHAR = s; } catch (e) {}
function heroName() { return CHARACTERS[CURRENT_CHAR].name; }
function fmtHero(s) { return String(s).replace(/\{HERO\}/g, heroName()); }

const SPRITES = {};                  // id -> { ok, img: {frame: Image} }
function loadCharacter(id) {
  const ch = CHARACTERS[id];
  if (!ch || ch.kind !== "sheet") return Promise.resolve(true);
  if (SPRITES[id] && SPRITES[id].promise) return SPRITES[id].promise;
  const S = SPRITES[id] = { ok: false, img: {} };
  const FR = SHEET_FRAMES.concat(ch.meta.run || []);
  S.promise = Promise.all(FR.map(f => loadImage(ch.dir + f + ".png").then(img => { S.img[f] = img; }))).then(() => {
    S.ok = FR.every(f => S.img[f] && S.img[f].width > 0);
    if (!S.ok && window.console) console.warn("sprite set incomplete for " + id + " - using the procedural fallback");
    return S.ok;
  });
  return S.promise;
}
function sheetReady(id) { return !!(SPRITES[id] && SPRITES[id].ok); }

// Toy pulse blaster drawn on the canvas (used when a sprite frame has no blaster in the hands).
// (x, y) = where the hand grips it; it points to the right.
function drawBlaster(ctx, x, y, s, flash) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  ctx.lineJoin = "round"; ctx.lineWidth = 1.6; ctx.strokeStyle = "#5b1138";
  ctx.fillStyle = "#17b8b0"; ctx.beginPath(); ctx.roundRect(-4, 1, 9, 13, 3); ctx.fill(); ctx.stroke();          // grip
  ctx.fillStyle = "#ff4fa0"; ctx.beginPath(); ctx.roundRect(-9, -9, 33, 13, 4); ctx.fill(); ctx.stroke();        // body
  ctx.fillStyle = "#17b8b0"; ctx.beginPath(); ctx.roundRect(22, -7, 13, 9, 3); ctx.fill(); ctx.stroke();         // barrel
  ctx.fillStyle = "#ff9f1c"; ctx.beginPath(); ctx.roundRect(34, -6, 5, 7, 2); ctx.fill(); ctx.stroke();          // tip
  ctx.fillStyle = "rgba(255,255,255,0.55)"; ctx.fillRect(-5, -7, 24, 2.2);                                       // gloss
  ctx.fillStyle = "#ffe14d"; ctx.beginPath(); ctx.arc(5, -3, 2.2, 0, 6.3); ctx.fill();                           // light
  if (flash > 0) {
    ctx.globalAlpha = flash; ctx.fillStyle = "#fff3a0";
    ctx.beginPath();
    for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4, r = i % 2 ? 7 : 14; ctx.lineTo(44 + Math.cos(a) * r, -3 + Math.sin(a) * r); }
    ctx.closePath(); ctx.fill();
  }
  ctx.restore();
}
// A small skateboard (BIZA + fallback): deck, trucks, spinning wheels.
function drawBoardUnder(ctx, x, y, t) {
  ctx.save(); ctx.translate(x, y);
  ctx.lineJoin = "round"; ctx.lineWidth = 1.5; ctx.strokeStyle = "#3a2410";
  ctx.fillStyle = "#e8683a"; ctx.beginPath(); ctx.roundRect(-30, -9, 62, 6, 3); ctx.fill(); ctx.stroke();
  ctx.fillStyle = "#222";
  for (const wx of [-19, 21]) { ctx.beginPath(); ctx.arc(wx, -3, 4.4, 0, 6.3); ctx.fill(); ctx.fillStyle = "#ffd23f"; ctx.fillRect(wx - 1, -4 + Math.sin(t * 30 + wx) * 1.5, 2, 2); ctx.fillStyle = "#222"; }
  ctx.restore();
}

function blendK(f) { const x = clamp((f - 0.22) / 0.56, 0, 1); return x * x * (3 - 2 * x); }
const MAX_JUMPS = 3;              // ground jump + TWO mid-air jumps (triple jump)
const JUMP_AIR_MULTS = [0.74, 0.60]; // 2nd and 3rd jump strength (relative to the ground jump)
const JUMP_HOLD_WINDOW = 0.16;    // seconds you can hold to add extra height
const JUMP_HOLD_ACCEL = 1450;     // extra upward accel applied while held, within window
const JUMP_CUT_FLOOR = JUMP_VELOCITY * 0.42; // releasing early clamps vy to (at least) this
const CEIL_FEET_Y = PLAYER_H + 44;           // feet can't go higher than this (keeps GUPTA on screen)
let cartoonBroken = false;        // set if the procedural art ever throws -> sprite fallback

class Player {
  constructor() {
    this.y = GROUND_Y;
    this.vy = 0;
    this.grounded = true;
    this.state = "run";
    this.animTime = 0;
    this.lives = DIFF().lives;
    this.invuln = 0;
    this.shield = false;
    this.jumpsUsed = 0;
    this.holding = false;
    this.holdTime = 0;
    this.doubleJumpFx = 0;   // brief visual flourish timer for mid-air jumps
    this.flipFx = 0;         // GUPTA somersaults on the 2nd/3rd jump
    this.hasBoots = false;   // set by Game while the Rocket Boots power-up is active
    this.ride = false;       // true during Quantum Taxi / Skateboard (smash-through, can't be hurt)
    this.rideKind = "";      // "taxi" | "board"
    this.hasGun = false;     // set by Game while the blaster has ammo
    this.shootTimer = 0;
    this.hurtTimer = 0;
    this.squash = 0;
    this.shopLock = false;   // true while GUPTA is inside the Sospana Sonke shop
    this.entryK = 0;         // 0..1 how far GUPTA has "gone into" the shop door
    this.landImpact = 0;     // set on landing so Game can puff some dust
    this._initAnim();
  }

  get maxJumps() { return MAX_JUMPS + (this.hasBoots ? 1 : 0); }
  get jumpsLeft() { return Math.max(0, this.maxJumps - this.jumpsUsed); }

  // Forgiving hitbox (smaller than the drawn character)
  get hitbox() {
    const w = PLAYER_W * DIFF().hitW;
    const h = PLAYER_H * DIFF().hitH;
    const cx = PLAYER_X + 10;
    const topY = this.y - h;
    return { x: cx - w / 2, y: topY, w, h };
  }

  // Press: grounded -> normal jump. Airborne with jumps left -> 2nd / 3rd jump (+1 with boots).
  jumpDown() {
    if (this.shopLock) return;
    if (this.grounded) {
      this.vy = JUMP_VELOCITY;
      this.grounded = false;
      this.jumpsUsed = 1;
      this.state = "jump";
      this.holding = true;
      this.holdTime = 0;
      this.jumpT = 0;
      Audio_.jump(0);
    } else if (this.jumpsUsed < this.maxJumps) {
      const m = JUMP_AIR_MULTS[Math.min(this.jumpsUsed - 1, JUMP_AIR_MULTS.length - 1)] || 0.55;
      this.vy = JUMP_VELOCITY * m;
      this.jumpsUsed++;
      this.holding = true;
      this.holdTime = 0;
      this.doubleJumpFx = 0.35;
      this.flipFx = 0.42;
      this.jumpT = 0;
      Audio_.jump(this.jumpsUsed - 1);
    }
  }

  // Release: cuts the jump short if released early (tap = hop, hold = full height).
  jumpUp() {
    this.holding = false;
    if (this.vy < JUMP_CUT_FLOOR) this.vy = JUMP_CUT_FLOOR;
  }

  hit() {
    if (this.ride || this.shopLock) return false;
    if (this.invuln > 0) return false;
    this.invuln = DIFF().invuln;
    if (this.shield) {
      this.shield = false;
      Audio_.powerup();
      return false;
    }
    this.lives--;
    this.hurtTimer = 0.7;
    Audio_.lifeLost();
    return true;
  }

  _stepPx() { const ch = CHARACTERS[CURRENT_CHAR]; return (ch.meta && ch.meta.stepPx) || 95; }

  update(dt) {
    this._dtDraw = dt;
    this.jumpT += dt; this.landT += dt;
    if (!this.grounded) {
      if (this.holding && this.holdTime < JUMP_HOLD_WINDOW && this.vy < 0) {
        this.vy -= JUMP_HOLD_ACCEL * dt;
        this.holdTime += dt;
      }
      this.vy += GRAVITY * dt;
      this.y += this.vy * dt;
      if (this.y < CEIL_FEET_Y) { this.y = CEIL_FEET_Y; if (this.vy < 0) this.vy = 0; }
      if (this.y >= GROUND_Y) {
        this.y = GROUND_Y;
        this.landImpact = this.vy;
        this.squash = Math.min(1, this.vy / 900);
        this.vy = 0;
        this.landT = 0;
        this.grounded = true;
        this.jumpsUsed = 0;
        this.holding = false;
        this.state = "run";
      }
    } else {
      this.y = GROUND_Y;
    }
    if (this.invuln > 0) this.invuln -= dt;
    if (this.doubleJumpFx > 0) this.doubleJumpFx -= dt;
    if (this.flipFx > 0) this.flipFx -= dt;
    if (this.shootTimer > 0) this.shootTimer -= dt;
    if (this.hurtTimer > 0) this.hurtTimer -= dt;
    if (this.squash > 0) this.squash = Math.max(0, this.squash - dt * 7);
    this.animTime += dt;
    // stride-synced run cycle: the phase advances with the ground distance covered, not with the clock (so feet never skate)
    if (this.grounded) this.runPhase += (this.worldSpeed * dt) / this._stepPx();
    const leanTarget = this.grounded && !this.ride ? clamp((this.worldSpeed - 200) / 260, 0, 1) * 0.06 : 0;
    this.leanNow += (leanTarget - this.leanNow) * (1 - Math.exp(-dt * 8));
  }

  _drawEffects(ctx, w, h) {
    if (this.shield) {
      ctx.save();
      ctx.globalAlpha = 0.35 + 0.15 * Math.sin(this.animTime * 8);
      ctx.fillStyle = "#5ad1ff";
      ctx.beginPath();
      ctx.ellipse(PLAYER_X + 10, this.y - h / 2, w * 0.72, h * 0.62, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
    // mid-air jump flourish: an expanding ring under the feet
    if (this.doubleJumpFx > 0) {
      const t = 1 - this.doubleJumpFx / 0.35;
      ctx.save();
      ctx.globalAlpha = (1 - t) * 0.8;
      ctx.strokeStyle = "#ffd23f";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.ellipse(PLAYER_X + 10, this.y - 6, 14 + t * 26, 6 + t * 10, 0, 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();
    }
    // Quantum Taxi: a glowing minibus taxi carrying GUPTA
    if (this.ride && this.rideKind === "taxi") {
      ctx.save();
      ctx.translate(PLAYER_X + 8, this.y + 2);
      ctx.scale(0.95, 0.95);
      ctx.globalAlpha = 0.82;
      ctx.shadowColor = "#5ad1ff"; ctx.shadowBlur = 18;
      Vec.taxi(ctx, 0, 0, this.animTime * 18);
      ctx.restore();
    }
  }

  draw(ctx) {
    const shopping = this.shopLock || this.entryK > 0;
    const ch = CHARACTERS[CURRENT_CHAR];
    if (ch.kind === "sheet") {
      if (sheetReady(ch.id)) {
        try { this._drawSheet(ctx, shopping, ch); return; }
        catch (e) { SPRITES[ch.id].ok = false; if (window.console) console.warn("sprite draw failed for " + ch.id, e); }
      }
      if (USE_CARTOON_GUPTA && !cartoonBroken) {
        try { this._drawCartoon(ctx, shopping); return; }
        catch (e) { cartoonBroken = true; if (window.console) console.warn("procedural hero failed, using legacy sprites", e); }
      }
    }
    this._drawSprite(ctx, shopping);   // BIZA (original sprites) - and the last-resort fallback
  }

  // where a blaster shot leaves the hero
  muzzle() {
    const ch = CHARACTERS[CURRENT_CHAR], x0 = PLAYER_X + 8;
    if (ch.kind === "sheet" && sheetReady(ch.id) && this.grounded) {
      const m = ch.meta;
      if (this.shootTimer > 0) return { x: x0 + (m.tip[0] - m.ax) * HERO_DS + 2, y: this.y + (m.tip[1] - m.ay) * HERO_DS };
      const f = this._fist || m.fist.run01;
      return { x: x0 + (f[0] - m.ax) * HERO_DS + 30, y: this.y + (f[1] - m.ay) * HERO_DS - 1 };
    }
    return { x: x0 + 44, y: this.y - 52 };
  }

  /* ---- v3.1 animation state (all dt-based; nothing here depends on the frame rate) ---- */
  _initAnim() {
    this.worldSpeed = 230;     // set by Game each frame (effective ground speed, px/s)
    this.runPhase = 0;         // steps taken (1.0 = one step of the run cycle), advanced by DISTANCE not time
    this.jumpT = 9;            // seconds since the last jump press
    this.airT = 0;             // seconds airborne
    this.landT = 9;            // seconds since touching down
    this.leanNow = 0;          // smoothed forward lean (radians)
    this._prevVis = null; this._vis = null; this._xf = 1;
    this._fist = null;         // blaster grip point (sprite px) of the frame being shown
  }

  // Which frames to show right now: a list of {img, a} layers (cross-dissolved) + the grip point of the blaster.
  _resolveSheet(S, ch) {
    const m = ch.meta, img = S.img;
    const shop = this.shopLock || this.entryK > 0;
    const sig = (s, layers, fist, extra) => Object.assign({ sig: s, layers, fist: fist || null }, extra || {});
    if (this.hurtTimer > 0) return sig("hurt", [{ img: img.hurt, a: 1 }]);
    if (this.ride && this.rideKind === "board") return sig("board", [{ img: img.board, a: 1 }], m.fist.board);
    if (!this.grounded) {
      if (this.flipFx > 0 && this.jumpsUsed >= 2) return sig("tuck", [{ img: img.tuck, a: 1 }], m.fist.tuck);
      if (this.jumpT < 0.04 && this.jumpsUsed === 1) return sig("crouch", [{ img: img.crouch, a: 1 }], m.fist.crouch, { sq: 0.05 });    // anticipation / push-off
      if (this.vy < -230) return sig("jump_up", [{ img: img.jump_up, a: 1 }], m.fist.jump_up);                                          // rise
      if (this.vy < 230) return sig("tuck", [{ img: img.tuck, a: 1 }], m.fist.tuck);                                                    // apex
      return sig("jump_fall", [{ img: img.jump_fall, a: 1 }], m.fist.jump_fall);                                                        // fall
    }
    if (this.landT < 0.085) return sig("crouch", [{ img: img.crouch, a: 1 }], m.fist.crouch);                                           // landing squash pose
    if (this.hasGun && this.shootTimer > 0) return sig("aim", [{ img: img.aim, a: 1 }]);
    if (this.worldSpeed < 25 && !this.ride) return sig("idle", [{ img: img.idle, a: 1 }], m.fist.idle, { breathe: true });              // standing: idle breathing
    // run cycle: stride-synced, time-warped (frames sit where the feet are), cross-dissolved
    const T = m.runT, n = T.length, p = this.runPhase - Math.floor(this.runPhase);
    let i = 0; while (i + 1 < n && T[i + 1] <= p) i++;
    const j = (i + 1) % n, t1 = j === 0 ? 1 : T[j], f = blendK(clamp((p - T[i]) / Math.max(1e-4, t1 - T[i]), 0, 1));
    const A = m.fist[m.run[i]], B = m.fist[m.run[j]];
    return sig("run", [{ img: img[m.run[i]], a: Math.min(1, 2 * (1 - f)) }, { img: img[m.run[j]], a: f }],
      [lerp(A[0], B[0], f), lerp(A[1], B[1], f)], { run: true });
  }

  // draw a visual with a short cross-fade whenever the pose changes (idle->run, run->jump, land, aim ...)
  _compose(ctx, vis, drawLayer, dt) {
    if (!this._vis || this._vis.sig !== vis.sig) {          // the run cycle is blended per frame; only a change of POSE cross-fades
      this._prevVis = this._vis || null;
      this._xf = this._vis ? 0 : 1;
    }
    this._vis = vis;
    const fadeDur = vis.sig === "hurt" ? 0.04 : 0.075;
    if (this._xf < 1) this._xf = Math.min(1, this._xf + (dt || 1 / 60) / fadeDur);
    const x = this._xf, pv = this._prevVis;
    if (pv && x < 1) { const k = Math.min(1, 2 * (1 - x)); for (const L of pv.layers) drawLayer(L.img, L.a * k); }
    for (const L of vis.layers) drawLayer(L.img, L.a * x);
  }

  _drawSheet(ctx, shopping, ch) {
    const S = SPRITES[ch.id], m = ch.meta, k = this.entryK || 0, dt = this._dtDraw || 1 / 60;
    const flicker = !shopping && this.invuln > 0 && this.hurtTimer <= 0 && Math.floor(this.invuln * 14) % 2 === 0;
    const grounded = this.grounded;
    const vis0 = this._resolveSheet(S, ch);
    for (const L of vis0.layers) if (!L.img || !L.img.width) L.img = S.img.idle;
    // ground shadow (shrinks while airborne, breathes with the stride)
    ctx.save();
    const air = clamp((GROUND_Y - this.y) / 220, 0, 1);
    const stride = vis0.run ? 1 + 0.06 * Math.cos(this.runPhase * Math.PI * 2) : 1;
    ctx.globalAlpha = 0.28 * (1 - air * 0.6) * (1 - k);
    ctx.fillStyle = "#000";
    ctx.beginPath(); ctx.ellipse(PLAYER_X + 9, GROUND_Y + 3, 28 * stride * (1 - air * 0.4), 5, 0, 0, Math.PI * 2); ctx.fill();
    ctx.restore();

    ctx.save();
    this._drawEffects(ctx, PLAYER_W, PLAYER_H);
    const fl = (this.flipFx > 0 && this.jumpsUsed >= 2 && !grounded) ? (1 - this.flipFx / 0.42) : 0;
    ctx.translate(PLAYER_X + 8, this.y);
    if (k > 0.001) ctx.scale(1 - 0.35 * k, 1 - 0.35 * k);
    let sx = 1, sy = 1;
    if (grounded) { sy = 1 - this.squash * 0.14; sx = 1 + this.squash * 0.12; }
    else { const st = clamp(Math.abs(this.vy) / 1800, 0, 0.5) * 0.16; sy = 1 + st; sx = 1 - st * 0.7; }
    if (vis0.sq) { sy *= 1 - vis0.sq; sx *= 1 + vis0.sq * 0.8; }
    if (vis0.breathe) sy *= 1 + 0.012 * Math.sin(this.animTime * 2.4);
    if (this.hurtTimer > 0.35) ctx.translate(rand(-2, 2), 0);
    // forward lean grows with speed (rotates around the feet); the somersault takes over in the air
    if (fl > 0) { const cy = -m.h * HERO_DS * 0.4; ctx.translate(0, cy); ctx.rotate(fl * Math.PI * 2); ctx.translate(0, -cy); }
    else if (this.leanNow) ctx.rotate(this.leanNow);
    ctx.scale(HERO_DS * sx, HERO_DS * sy);
    const base = (flicker ? 0.5 : 1) * (1 - k);
    this._compose(ctx, vis0, (img, a) => { if (a <= 0.003) return; ctx.globalAlpha = base * a; ctx.drawImage(img, -m.ax, -m.ay); }, dt);
    ctx.globalAlpha = 1 - k;
    this._fist = vis0.fist;
    if (this.hasGun && grounded && vis0.run && vis0.fist) {            // toy blaster rides in the front hand, following the frame
      const f = vis0.fist; drawBlaster(ctx, f[0] - m.ax - 6, f[1] - m.ay + 3, 1.9, 0);
    }
    if (vis0.sig === "aim" && this.shootTimer > 0.12) {                // muzzle flash
      ctx.fillStyle = "rgba(255,243,160," + clamp((this.shootTimer - 0.12) / 0.1, 0, 1).toFixed(2) + ")";
      ctx.beginPath();
      for (let i = 0; i < 10; i++) { const a = i * Math.PI / 5, r = i % 2 ? 9 : 22; ctx.lineTo(m.tip[0] - m.ax + 8 + Math.cos(a) * r, m.tip[1] - m.ay + Math.sin(a) * r); }
      ctx.closePath(); ctx.fill();
    }
    ctx.restore();
  }

  _drawCartoon(ctx, shopping) {
    const flicker = !shopping && this.invuln > 0 && this.hurtTimer <= 0 && Math.floor(this.invuln * 14) % 2 === 0;
    const k = this.entryK || 0;
    ctx.save();
    // ground shadow (shrinks while in the air)
    const air = clamp((GROUND_Y - this.y) / 220, 0, 1);
    ctx.globalAlpha = 0.25 * (1 - air * 0.6) * (1 - k);
    ctx.fillStyle = "#000";
    ctx.beginPath(); ctx.ellipse(PLAYER_X + 9, GROUND_Y + 3, 26 * (1 - air * 0.4), 5, 0, 0, Math.PI * 2); ctx.fill();
    ctx.restore();

    ctx.save();
    this._drawEffects(ctx, PLAYER_W, PLAYER_H);
    let state = "run";
    if (this.hurtTimer > 0) state = "hurt";
    else if (this.ride && this.rideKind === "board") state = "board";
    else if (!this.grounded) state = "jump";
    if (k > 0.001) {                       // stepping into the shop door: shrink + fade
      ctx.translate(PLAYER_X + 8, this.y); ctx.scale(1 - 0.35 * k, 1 - 0.35 * k); ctx.translate(-(PLAYER_X + 8), -this.y);
    }
    GuptaArt.draw(ctx, {
      x: PLAYER_X + 8, y: this.y, scale: 0.95, facing: 1, state,
      t: this.animTime, vy: this.vy, noShadow: true,
      gun: this.hasGun, shoot: clamp(this.shootTimer / 0.22, 0, 1),
      flip: (this.flipFx > 0 && this.jumpsUsed >= 2 && !this.grounded) ? (1 - this.flipFx / 0.42) : 0,
      squash: this.grounded ? this.squash : clamp(-this.vy / 1800, -0.35, 0.5) * 0.6,
      hurtShake: this.hurtTimer > 0.35,
      alpha: (flicker ? 0.45 : 1) * (1 - k)
    });
    ctx.restore();
  }

  _drawSprite(ctx, shopping) {
    const flicker = this.invuln > 0 && !shopping && Math.floor(this.invuln * 16) % 2 === 0;
    if (flicker) return;
    const dt = this._dtDraw || 1 / 60;
    let vis;
    if (this.state === "jump" || !this.grounded) {
      const frames = IMAGES.hero_jump;
      let idx;
      if (this.vy < -260) idx = 0;
      else if (this.vy < 0) idx = 1;
      else if (this.vy < 260) idx = 2;
      else idx = 3;
      vis = { sig: "j" + idx, layers: [{ img: frames[idx], a: 1 }] };
    } else {
      // original 5 run frames, driven by distance and cross-dissolved (no hard frame snaps)
      const frames = IMAGES.hero_run_right, n = frames.length;
      const q = (((this.runPhase / 2) % 1) + 1) % 1 * n, i = Math.floor(q) % n, f = blendK(q - Math.floor(q)), j = (i + 1) % n;
      vis = { sig: "run", layers: [{ img: frames[i], a: Math.min(1, 2 * (1 - f)) }, { img: frames[j], a: f }], run: true };
    }
    if (!vis.layers.every(L => L.img && L.img.width)) return;
    const h = PLAYER_H;
    const onBoard = this.ride && this.rideKind === "board";
    const bob = vis.run && !onBoard ? 1.8 * Math.abs(Math.sin(this.runPhase * Math.PI)) : 0;     // one bounce per step
    const k = this.entryK || 0;
    ctx.save();
    this._drawEffects(ctx, PLAYER_W * 1.1, h);
    if (onBoard) { ctx.globalAlpha = 1 - k; drawBoardUnder(ctx, PLAYER_X + 8, this.y, this.animTime); }
    ctx.translate(PLAYER_X + 10, this.y - (onBoard ? 8 : 0) - bob);
    if (this.leanNow && this.grounded) ctx.rotate(this.leanNow);
    const sq = this.grounded ? this.squash : 0;
    ctx.scale(1 + sq * 0.10, 1 - sq * 0.12);
    this._compose(ctx, vis, (img, a) => {
      if (a <= 0.003) return;
      const w = (img.width / img.height) * h;
      ctx.globalAlpha = a * (1 - k);
      ctx.drawImage(img, -w / 2, -h, w, h);
    }, dt);
    ctx.globalAlpha = 1 - k;
    if (this.hasGun && this.grounded && !(k > 0)) {                         // toy blaster in the front hand (follows the bob)
      drawBlaster(ctx, 0.24 * (vis.layers[0].img.width / vis.layers[0].img.height) * h, -h * 0.5, 0.95, this.shootTimer > 0.12 ? 1 : 0);
    }
    ctx.restore();
  }
}

/* ---------------------------------------------------------
   ORIGINAL VECTOR ART
   The source pack has no dog / taxi / pedestrian / house / pole
   sprites (see header note), so these are drawn directly with
   canvas primitives — simple, flat, silhouette-style, and fast.
--------------------------------------------------------- */
const Vec = {
  dog(ctx, x, groundY, t, color) {
    color = color || "#5a4632";
    const bob = Math.abs(Math.sin(t * 10)) * 4;
    const y = groundY - 20 - bob;
    ctx.save();
    ctx.translate(x, y);
    ctx.fillStyle = "rgba(0,0,0,0.25)";
    ctx.beginPath(); ctx.ellipse(0, 24 + bob, 22, 5, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = color;
    // body
    ctx.beginPath();
    ctx.ellipse(0, 4, 20, 11, 0, 0, Math.PI * 2);
    ctx.fill();
    // head
    ctx.beginPath();
    ctx.ellipse(20, -4, 9, 8, 0, 0, Math.PI * 2);
    ctx.fill();
    // ear
    ctx.beginPath();
    ctx.moveTo(24, -10); ctx.lineTo(28, -18); ctx.lineTo(20, -12); ctx.closePath();
    ctx.fill();
    // tail
    ctx.beginPath();
    ctx.moveTo(-18, -2);
    ctx.quadraticCurveTo(-30, -12 - bob, -26, -2);
    ctx.lineWidth = 4; ctx.strokeStyle = color; ctx.stroke();
    // legs (simple alternating)
    const legSwing = Math.sin(t * 14) * 6;
    ctx.strokeStyle = color; ctx.lineWidth = 4; ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(-10, 12); ctx.lineTo(-10 + legSwing, 24); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(8, 12); ctx.lineTo(8 - legSwing, 24); ctx.stroke();
    ctx.restore();
  },

  pedestrian(ctx, x, groundY, t, shirt) {
    shirt = shirt || "#c1502e";
    const walk = Math.sin(t * 8);
    ctx.save();
    ctx.translate(x, groundY);
    ctx.fillStyle = "rgba(0,0,0,0.22)";
    ctx.beginPath(); ctx.ellipse(0, 2, 12, 4, 0, 0, Math.PI * 2); ctx.fill();
    // legs
    ctx.strokeStyle = "#2a2118"; ctx.lineWidth = 5; ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(0, -30); ctx.lineTo(walk * 8, 0); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, -30); ctx.lineTo(-walk * 8, 0); ctx.stroke();
    // body
    ctx.fillStyle = shirt;
    ctx.beginPath();
    ctx.roundRect(-9, -58, 18, 30, 6);
    ctx.fill();
    // arms
    ctx.strokeStyle = shirt; ctx.lineWidth = 4.5;
    ctx.beginPath(); ctx.moveTo(0, -54); ctx.lineTo(-walk * 7, -30); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, -54); ctx.lineTo(walk * 7, -30); ctx.stroke();
    // head
    ctx.fillStyle = "#4a3423";
    ctx.beginPath(); ctx.arc(0, -66, 8, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  },

  taxi(ctx, x, groundY, wheelSpin) {
    ctx.save();
    ctx.translate(x, groundY);
    ctx.fillStyle = "rgba(0,0,0,0.28)";
    ctx.beginPath(); ctx.ellipse(0, 4, 62, 8, 0, 0, Math.PI * 2); ctx.fill();
    // body
    const grad = ctx.createLinearGradient(-60, -50, -60, 0);
    grad.addColorStop(0, "#f2f2ef"); grad.addColorStop(1, "#c9c9c2");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.roundRect(-60, -34, 120, 34, 8);
    ctx.fill();
    ctx.beginPath();
    ctx.roundRect(-42, -54, 78, 24, 7);
    ctx.fill();
    // stripe (taxi livery)
    ctx.fillStyle = "#2a63c9";
    ctx.fillRect(-60, -18, 120, 7);
    // windows
    ctx.fillStyle = "#213040";
    ctx.beginPath(); ctx.roundRect(-38, -50, 30, 18, 3); ctx.fill();
    ctx.beginPath(); ctx.roundRect(4, -50, 32, 18, 3); ctx.fill();
    // wheels
    const spin = wheelSpin % (Math.PI * 2);
    [[-38, 2], [34, 2]].forEach(([wx, wy]) => {
      ctx.save();
      ctx.translate(wx, wy);
      ctx.fillStyle = "#181818";
      ctx.beginPath(); ctx.arc(0, 0, 11, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = "#888"; ctx.lineWidth = 2;
      ctx.rotate(spin);
      ctx.beginPath(); ctx.moveTo(-8, 0); ctx.lineTo(8, 0); ctx.moveTo(0, -8); ctx.lineTo(0, 8); ctx.stroke();
      ctx.restore();
    });
    // headlight glow
    ctx.fillStyle = "rgba(255,230,150,0.9)";
    ctx.beginPath(); ctx.arc(58, -14, 3.5, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  },

  // Corrugated-iron (zinc) shack made of mismatched sheets
  zincShack(ctx, x, groundY, seed) {
    const cols = ["#9aa0a6", "#b5532e", "#6f8fa3", "#7a9a6a", "#c9c3b0"];
    const w = 66 + (seed % 3) * 12, h = 44 + (seed % 4) * 6;
    ctx.save();
    ctx.translate(x, groundY);
    ctx.fillStyle = "rgba(0,0,0,0.2)"; ctx.fillRect(-w / 2, 2, w, 4);
    let px = -w / 2, i = 0;
    while (px < w / 2) {
      const pw = Math.min(13 + ((i * 5 + seed) % 9), w / 2 - px), top = -h + ((i * 3) % 7);
      ctx.fillStyle = cols[(i + seed) % cols.length]; ctx.fillRect(px, top, pw, -top);
      ctx.fillStyle = "rgba(0,0,0,0.18)";
      for (let k = px + 2; k < px + pw; k += 4) ctx.fillRect(k, top, 1, -top);
      px += pw; i++;
    }
    ctx.fillStyle = "#7d838a";
    ctx.beginPath(); ctx.moveTo(-w / 2 - 4, -h + 2); ctx.lineTo(w / 2 + 4, -h - 8); ctx.lineTo(w / 2 + 4, -h - 3); ctx.lineTo(-w / 2 - 4, -h + 7); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = "#1c1c1c"; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.ellipse(-w / 6, -h - 3, 7, 3, 0, 0, Math.PI * 2); ctx.stroke();
    ctx.fillStyle = "#6b4a2b"; ctx.fillRect(-5, -26, 12, 26);
    ctx.fillStyle = "#1b2630"; ctx.fillRect(w / 2 - 20, -h + 14, 12, 10);
    ctx.restore();
  },

  // RDP "matchbox" house: plain box, low roof, burglar-barred windows
  matchbox(ctx, x, groundY, seed) {
    const walls = ["#e0a63e", "#c9582f", "#ecd8a6", "#86b46a", "#8fb3d1"];
    const w = 70 + (seed % 3) * 10, h = 50;
    ctx.save();
    ctx.translate(x, groundY);
    ctx.fillStyle = "rgba(0,0,0,0.2)"; ctx.fillRect(-w / 2, 2, w, 4);
    ctx.fillStyle = walls[seed % walls.length]; ctx.fillRect(-w / 2, -h, w, h);
    ctx.fillStyle = "rgba(0,0,0,0.12)"; ctx.fillRect(-w / 2, -8, w, 8);
    ctx.fillStyle = "#6b6f73";
    ctx.beginPath(); ctx.moveTo(-w / 2 - 5, -h); ctx.lineTo(0, -h - 16); ctx.lineTo(w / 2 + 5, -h); ctx.closePath(); ctx.fill();
    ctx.fillStyle = "#3a2b1c"; ctx.fillRect(-7, -26, 14, 26);
    ctx.fillStyle = "#dff0ff"; ctx.globalAlpha = 0.8;
    ctx.fillRect(-w / 2 + 8, -h + 12, 14, 12); ctx.fillRect(w / 2 - 22, -h + 12, 14, 12);
    ctx.globalAlpha = 1; ctx.strokeStyle = "rgba(20,20,20,0.8)"; ctx.lineWidth = 1;
    [-w / 2 + 8, w / 2 - 22].forEach(wx => { ctx.beginPath(); ctx.moveTo(wx + 7, -h + 12); ctx.lineTo(wx + 7, -h + 24); ctx.moveTo(wx, -h + 18); ctx.lineTo(wx + 14, -h + 18); ctx.stroke(); });
    ctx.restore();
  },

  // rolling tyre hazard (kasi classic)
  tyre(ctx, x, groundY, rot) {
    ctx.save(); ctx.translate(x, groundY - 21);
    ctx.fillStyle = "rgba(0,0,0,0.25)"; ctx.beginPath(); ctx.ellipse(0, 21, 20, 4, 0, 0, Math.PI * 2); ctx.fill();
    ctx.rotate(rot);
    ctx.beginPath(); ctx.arc(0, 0, 21, 0, Math.PI * 2); ctx.fillStyle = "#1b1b1b"; ctx.fill();
    ctx.strokeStyle = "#3b3b3b"; ctx.lineWidth = 2;
    for (let i = 0; i < 12; i++) { const a = i * Math.PI / 6; ctx.beginPath(); ctx.moveTo(Math.cos(a) * 17, Math.sin(a) * 17); ctx.lineTo(Math.cos(a) * 21, Math.sin(a) * 21); ctx.stroke(); }
    ctx.beginPath(); ctx.arc(0, 0, 11, 0, Math.PI * 2); ctx.fillStyle = "#8d949b"; ctx.fill();
    ctx.strokeStyle = "#5c6269"; ctx.lineWidth = 2;
    for (let i = 0; i < 5; i++) { const a = i * Math.PI * 2 / 5; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(Math.cos(a) * 10, Math.sin(a) * 10); ctx.stroke(); }
    ctx.beginPath(); ctx.arc(0, 0, 3, 0, Math.PI * 2); ctx.fillStyle = "#333"; ctx.fill();
    ctx.restore();
  },

  goat(ctx, x, groundY, t, col) {
    const sw = Math.sin(t * 6) * 3;
    ctx.save(); ctx.translate(x, groundY);
    ctx.fillStyle = "rgba(0,0,0,0.22)"; ctx.beginPath(); ctx.ellipse(0, 1, 16, 3, 0, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = col; ctx.lineWidth = 2.4; ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(-9, -10); ctx.lineTo(-9 + sw, 0); ctx.moveTo(-5, -10); ctx.lineTo(-5 - sw, 0);
    ctx.moveTo(7, -10); ctx.lineTo(7 - sw, 0); ctx.moveTo(11, -10); ctx.lineTo(11 + sw, 0); ctx.stroke();
    ctx.fillStyle = col; ctx.beginPath(); ctx.ellipse(0, -15, 15, 7, 0, 0, Math.PI * 2); ctx.fill();
    ctx.lineWidth = 4.5; ctx.beginPath(); ctx.moveTo(11, -17); ctx.lineTo(17, -24); ctx.stroke();
    ctx.beginPath(); ctx.ellipse(18, -25, 5, 3.6, 0.2, 0, Math.PI * 2); ctx.fill();
    ctx.lineWidth = 1.4; ctx.beginPath(); ctx.moveTo(17, -28); ctx.lineTo(14, -34); ctx.moveTo(20, -28); ctx.lineTo(22, -34); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-14, -18); ctx.lineTo(-18, -22); ctx.stroke();
    ctx.restore();
  },

  cow(ctx, x, groundY, t, col) {
    const sw = Math.sin(t * 4) * 3.5;
    ctx.save(); ctx.translate(x, groundY);
    ctx.fillStyle = "rgba(0,0,0,0.22)"; ctx.beginPath(); ctx.ellipse(0, 1, 28, 4, 0, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = col; ctx.lineWidth = 4; ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(-16, -18); ctx.lineTo(-16 + sw, 0); ctx.moveTo(-9, -18); ctx.lineTo(-9 - sw, 0);
    ctx.moveTo(12, -18); ctx.lineTo(12 - sw, 0); ctx.moveTo(19, -18); ctx.lineTo(19 + sw, 0); ctx.stroke();
    ctx.fillStyle = col; ctx.beginPath(); ctx.ellipse(0, -28, 25, 12, 0, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(28, -36, 9, 6.5, 0.2, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "rgba(0,0,0,0.28)"; ctx.beginPath(); ctx.ellipse(-6, -30, 7, 5, 0, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = "#e8dcc0"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(26, -42); ctx.lineTo(22, -49); ctx.moveTo(31, -42); ctx.lineTo(35, -48); ctx.stroke();
    ctx.strokeStyle = col; ctx.lineWidth = 1.8; ctx.beginPath(); ctx.moveTo(-24, -32); ctx.quadraticCurveTo(-30, -26 + sw, -28, -14); ctx.stroke();
    ctx.restore();
  },

  house(ctx, x, groundY, seed) {
    if (seed % 5 === 2) return Vec.zincShack(ctx, x, groundY, seed);
    if (seed % 5 === 4) return Vec.matchbox(ctx, x, groundY, seed);
    const variants = [
      { body: "#c98b4a", roof: "#7a3b2e" },
      { body: "#8fa9c9", roof: "#3d4f66" },
      { body: "#d9c48a", roof: "#8a5a3a" },
      { body: "#a8c98f", roof: "#4a5a34" },
      { body: "#c97a7a", roof: "#5a2f2f" }
    ];
    const v = variants[seed % variants.length];
    const w = 74 + (seed % 3) * 14;
    const h = 62 + (seed % 4) * 10;
    ctx.save();
    ctx.translate(x, groundY);
    ctx.fillStyle = "rgba(0,0,0,0.2)";
    ctx.fillRect(-w / 2, 2, w, 4);
    // body
    ctx.fillStyle = v.body;
    ctx.fillRect(-w / 2, -h, w, h);
    // roof
    ctx.fillStyle = v.roof;
    ctx.beginPath();
    ctx.moveTo(-w / 2 - 6, -h);
    ctx.lineTo(w / 2 + 6, -h);
    ctx.lineTo(w / 2 - 4, -h - 18);
    ctx.lineTo(-w / 2 + 4, -h - 18);
    ctx.closePath();
    ctx.fill();
    // door
    ctx.fillStyle = "#3a2b1c";
    ctx.fillRect(-9, -26, 18, 26);
    // windows
    ctx.fillStyle = "#dff0ff";
    ctx.globalAlpha = 0.85;
    ctx.fillRect(-w / 2 + 10, -h + 14, 14, 14);
    ctx.fillRect(w / 2 - 24, -h + 14, 14, 14);
    ctx.globalAlpha = 1;
    // spaza-shop flourish on some houses
    if (seed % 4 === 0) {
      ctx.fillStyle = "#e2b23a";
      ctx.fillRect(-w / 2 - 4, -h - 2, w + 8, 8);
      ctx.fillStyle = "#3a2b1c";
      ctx.font = "bold 8px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("SPAZA", 0, -h + 4);
    }
    ctx.restore();
  },

  pole(ctx, x, groundY, h, span) {
    h = h || 92; span = span || 132;
    ctx.save();
    ctx.translate(x, groundY);
    ctx.strokeStyle = "#4a4438";
    ctx.lineWidth = 4.5;
    ctx.beginPath(); ctx.moveTo(0, 4); ctx.lineTo(0, -h); ctx.stroke();
    ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(-17, -h + 8); ctx.lineTo(17, -h + 8); ctx.moveTo(-12, -h + 22); ctx.lineTo(12, -h + 22); ctx.stroke();
    // transformer drum on some poles
    if (h > 91) { ctx.fillStyle = "#6f757a"; ctx.fillRect(5, -h + 28, 10, 16); ctx.fillStyle = "#55595e"; ctx.fillRect(5, -h + 28, 10, 3); }
    // insulators + wires that run on to the next pole
    ctx.fillStyle = "#9ad0d6";
    const offs = [-15, 0, 15], sag = Math.min(34, 8 + span * 0.045);
    for (const ox of offs) {
      const y0 = -h + 8 + (ox === 0 ? -4 : 0);
      ctx.fillRect(ox - 1.5, y0 - 4, 3, 4);
      ctx.strokeStyle = "rgba(20,20,20,0.6)"; ctx.lineWidth = 1.3;
      ctx.beginPath(); ctx.moveTo(ox, y0); ctx.quadraticCurveTo(span / 2 + ox, y0 + 2 * sag, span + ox, y0); ctx.stroke();
    }
    // birds sitting on the wire
    ctx.fillStyle = "#1c1c1c";
    for (const u of [0.38, 0.45, 0.7]) {
      const y0 = -h + 8, bx = span * u, by = (1 - u) * (1 - u) * y0 + 2 * u * (1 - u) * (y0 + 2 * sag) + u * u * y0;
      ctx.beginPath(); ctx.ellipse(bx, by - 3, 3.4, 2.4, 0, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.arc(bx + 3, by - 5, 1.5, 0, Math.PI * 2); ctx.fill();
    }
    ctx.restore();
  }
};

/* ---------------------------------------------------------
   COLLECTIBLES
--------------------------------------------------------- */
const COLLECTIBLE_DEFS = {
  coin:     { value: 5,  score: 8,   kind: "coin" },
  gem:      { value: 15, score: 20,  kind: "gem" },
  moneybag: { value: 40, score: 40,  kind: "moneybag" },
  star:     { value: 0,  score: 50,  kind: "star" },
  heart:    { value: 0,  score: 15,  kind: "heart" }
};
const GEM_IMAGES = ["gem_green","gem_red","gem_blue","gem_purple","gem_rainbow"];

class Collectible {
  constructor(x, y, type) {
    this.x = x; this.y = y; this.type = type; this.dead = false;
    this.collected = false;
    this.t = rand(0, 6.28);
    if (type === "gem") this.gemKey = pick(GEM_IMAGES);
  }
  get hitbox() {
    const r = this.type === "moneybag" ? 20 : 16;
    return { x: this.x - r, y: this.y - r, w: r * 2, h: r * 2 };
  }
  update(dt, speed, magnetTarget) {
    this.x -= speed * dt;
    this.t += dt * 4;
    if (magnetTarget) {
      const dx = magnetTarget.x - this.x, dy = magnetTarget.y - this.y;
      const dist = Math.hypot(dx, dy);
      if (dist < 230) {
        this.x += dx * clamp(dt * 7, 0, 1);
        this.y += dy * clamp(dt * 7, 0, 1);
      }
    }
    if (this.x < -40) this.dead = true;
  }
  draw(ctx) {
    let img;
    if (this.type === "coin") {
      const frames = IMAGES.coin_spin;
      img = frames[Math.floor(this.t * 3) % frames.length];
    } else if (this.type === "gem") img = IMAGES[this.gemKey];
    else if (this.type === "moneybag") img = IMAGES.moneybag;
    else if (this.type === "star") img = IMAGES.star;
    else if (this.type === "heart") img = IMAGES.heart;
    if (!img || !img.width) return;
    const bob = Math.sin(this.t) * 6;
    const size = this.type === "moneybag" ? 34 : 28;
    ctx.save();
    ctx.translate(this.x, this.y + bob);
    if (this.type === "coin") ctx.rotate(Math.sin(this.t * 0.6) * 0.15);
    ctx.drawImage(img, -size / 2, -size / 2, size, size);
    ctx.restore();
  }
}

/* ---------------------------------------------------------
   GROUND OBSTACLES (sprite-based, jump required)
--------------------------------------------------------- */
const OBSTACLE_TYPES = [
  { key: "ob_rock1",    h: 46 },
  { key: "ob_rock2",    h: 52 },
  { key: "ob_rock3",    h: 44 },
  { key: "ob_rockpile", h: 68 },
  { key: "ob_crate",    h: 66 },
  { key: "ob_barrel",   h: 60 },
  { key: "ob_pot",      h: 42 },
  { key: "ob_spikes",   h: 26 }
];

class Obstacle {
  constructor(typeDef) {
    this.def = typeDef;
    this.x = CW + 60;
    this.dead = false;
    this.hp = 1;
    const img = IMAGES[typeDef.key];
    this.ratio = img && img.width ? img.width / img.height : 1;
  }
  get w() { return this.ratio * this.def.h; }
  get h() { return this.def.h; }
  get hitbox() {
    const w = this.w * 0.55, h = this.h * 0.8;
    return { x: this.x - w / 2, y: GROUND_Y - h, w, h };
  }
  update(dt, speed) {
    this.x -= speed * dt;
    if (this.x < -140) this.dead = true;
  }
  draw(ctx) {
    const img = IMAGES[this.def.key];
    if (!img || !img.width) return;
    const w = this.w, h = this.h;
    const y = GROUND_Y - h;
    ctx.save();
    ctx.globalAlpha = 0.28;
    ctx.fillStyle = "#000";
    ctx.beginPath();
    ctx.ellipse(this.x, GROUND_Y + 4, w * 0.34, 6, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.drawImage(img, this.x - w / 2, y, w, h);
    ctx.restore();
  }
}

/* ---------------------------------------------------------
   TALL STACK — a double-jump-only obstacle. Too tall to clear with a
   single jump (even a held one); rewards using the new double-jump.
--------------------------------------------------------- */
const STACK_COMBOS = [
  ["ob_crate", "ob_barrel"],
  ["ob_barrel", "ob_crate"],
  ["ob_rockpile", "ob_crate"],
  ["ob_crate", "ob_crate"]
];
class TallStack {
  constructor() {
    this.combo = pick(STACK_COMBOS);
    this.x = CW + 60;
    this.dead = false;
    this.hp = 2;
    // Sized so a quick tap-jump can't clear it, but a held jump or a
    // double jump both comfortably can — teaches players to use the new
    // hold/double-jump mechanics without being frustratingly precise.
    this.baseH = 72;
    this.topH = 62;
    const imgBase = IMAGES[this.combo[0]], imgTop = IMAGES[this.combo[1]];
    this.baseRatio = imgBase && imgBase.width ? imgBase.width / imgBase.height : 1;
    this.topRatio = imgTop && imgTop.width ? imgTop.width / imgTop.height : 1;
  }
  get h() { return this.baseH + this.topH - 6; } // slight overlap for a stacked look
  get hitbox() {
    const w = this.baseRatio * this.baseH * 0.34;
    const h = this.h * 0.8;
    return { x: this.x - w / 2, y: GROUND_Y - h, w, h };
  }
  update(dt, speed) {
    this.x -= speed * dt;
    if (this.x < -140) this.dead = true;
  }
  draw(ctx) {
    const imgBase = IMAGES[this.combo[0]], imgTop = IMAGES[this.combo[1]];
    ctx.save();
    ctx.globalAlpha = 0.28;
    ctx.fillStyle = "#000";
    ctx.beginPath();
    ctx.ellipse(this.x, GROUND_Y + 4, this.baseH * 0.4, 6, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
    if (imgBase && imgBase.width) {
      const w = this.baseRatio * this.baseH;
      ctx.drawImage(imgBase, this.x - w / 2, GROUND_Y - this.baseH, w, this.baseH);
    }
    if (imgTop && imgTop.width) {
      const w = this.topRatio * this.topH;
      ctx.drawImage(imgTop, this.x - w / 2, GROUND_Y - this.baseH - this.topH + 6, w, this.topH);
    }
    ctx.restore();
  }
}

/* ---------------------------------------------------------
   MOVING HAZARDS — a rolling tyre (default). The dog is kept in the code but
   only spawns when ROAD_DOGS is true. Jaywalking people are gone from the road.
--------------------------------------------------------- */
class MovingHazard {
  constructor(type) {
    this.type = type; // "tyre" | "dog"
    this.x = CW + 60;
    this.dead = false;
    this.hp = 1;
    this.t = rand(0, 6.28);
    this.color = type === "dog" ? pick(["#5a4632", "#3a2f22", "#8a6a44"]) : null;
  }
  get w() { return this.type === "dog" ? 56 : 44; }
  get h() { return this.type === "dog" ? 40 : 42; }
  get hitbox() {
    const w = this.w * 0.6, h = this.h * 0.75;
    return { x: this.x - w / 2, y: GROUND_Y - h, w, h };
  }
  update(dt, speed) {
    this.x -= (this.type === "tyre" ? speed + 90 : speed) * dt;
    this.t += dt;
    if (this.x < -80) this.dead = true;
  }
  draw(ctx) {
    ctx.save();
    if (this.type === "dog") Vec.dog(ctx, this.x, GROUND_Y, this.t, this.color);
    else Vec.tyre(ctx, this.x, GROUND_Y, this.t * -7);
    ctx.restore();
  }
}

/* ---------------------------------------------------------
   POWER-UPS (procedurally drawn icons — original art)
--------------------------------------------------------- */
const POWERUP_DEFS = {
  shield:  { icon: "🛡️", color: "#5ad1ff", label: "SHIELD" },
  magnet:  { icon: "🧲", color: "#ff5a3c", label: "MAGNET" },
  multi:   { icon: "⚡", color: "#ffd23f", label: "x2 CASH" },
  boots:   { icon: "🚀", color: "#ff8a3c", label: "ROCKET BOOTS" },
  taxi:    { icon: "🚕", color: "#ffd23f", label: "QUANTUM TAXI" },
  board:   { icon: "🛹", color: "#2ec4b6", label: "SKATEBOARD",
    draw(ctx, r) {   // cartoon skateboard icon
      ctx.save(); ctx.rotate(-0.25); ctx.lineJoin = "round";
      ctx.fillStyle = "#ff6b35"; ctx.strokeStyle = "#2a1810"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(-15, -4); ctx.quadraticCurveTo(-14, 3, -9, 3); ctx.lineTo(9, 3); ctx.quadraticCurveTo(14, 3, 15, -4); ctx.lineTo(13, -4); ctx.quadraticCurveTo(12, 0, 9, 0); ctx.lineTo(-9, 0); ctx.quadraticCurveTo(-12, 0, -13, -4); ctx.closePath(); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(-8, 7, 3.6, 0, Math.PI * 2); ctx.arc(8, 7, 3.6, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      ctx.restore();
    } },
  gun:     { icon: "", color: "#ff5fa2", label: "PULSE BLASTER",
    draw(ctx, r) {   // toy blaster icon (bright, cartoon)
      ctx.save(); ctx.rotate(-0.15); ctx.lineJoin = "round"; ctx.strokeStyle = "#2a1810"; ctx.lineWidth = 2;
      ctx.fillStyle = "#ffe14d"; ctx.beginPath(); ctx.moveTo(-6, 0); ctx.lineTo(0, 0); ctx.lineTo(2, 11); ctx.lineTo(-5, 11); ctx.closePath(); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#2ec4b6"; ctx.fillRect(-13, -9, 24, 10); ctx.strokeRect(-13, -9, 24, 10);
      ctx.fillStyle = "#ff9f1c"; ctx.fillRect(11, -8, 7, 8); ctx.strokeRect(11, -8, 7, 8);
      ctx.fillStyle = "#fff"; ctx.fillRect(-10, -7, 14, 2.4);
      ctx.restore();
    } }
};
class PowerUp {
  constructor(x, y, kind) {
    this.x = x; this.y = y; this.kind = kind; this.dead = false;
    this.t = rand(0, 6.28);
  }
  get hitbox() {
    const r = 22;
    return { x: this.x - r, y: this.y - r, w: r * 2, h: r * 2 };
  }
  update(dt, speed) {
    this.x -= speed * dt;
    this.t += dt * 3;
    if (this.x < -40) this.dead = true;
  }
  draw(ctx) {
    const def = POWERUP_DEFS[this.kind];
    const bob = Math.sin(this.t) * 7;
    const r = 22;
    ctx.save();
    ctx.translate(this.x, this.y + bob);
    ctx.globalAlpha = 0.85;
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, Math.PI * 2);
    ctx.fillStyle = def.color;
    ctx.shadowColor = def.color;
    ctx.shadowBlur = 14;
    ctx.fill();
    ctx.shadowBlur = 0;
    if (def.draw) def.draw(ctx, r);
    else {
      ctx.font = `${Math.floor(r * 1.15)}px sans-serif`;
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText(def.icon, 0, 1);
    }
    ctx.restore();
  }
}

/* ---------------------------------------------------------
   AMBIENT / BACKGROUND DRESSING (non-colliding, pure atmosphere)
--------------------------------------------------------- */
const DECOR_SPRITE_KEYS = ["dc_bush", "dc_tree", "dc_fence", "dc_signpost"];

class BackgroundProp {
  constructor(x, seed) {
    this.x = x; this.seed = seed;
    this.isSprite = seed % 3 === 0;
    this.spriteKey = pick(DECOR_SPRITE_KEYS);
  }
  update(dt, speed) { this.x -= speed * dt; }
  draw(ctx, rowY) {
    if (this.isSprite) {
      const img = IMAGES[this.spriteKey];
      if (!img || !img.width) return;
      const h = 58;
      const w = (img.width / img.height) * h;
      ctx.drawImage(img, this.x - w / 2, rowY - h, w, h);
    } else {
      Vec.house(ctx, this.x, rowY, this.seed);
    }
  }
}

class DecorPole {
  constructor(x) { this.x = x; this.h = rand(84, 100); this.span = 700; }
  update(dt, speed) { this.x -= speed * dt; }
  draw(ctx) { Vec.pole(ctx, this.x, GROUND_Y, this.h, this.span); }
}

// Walk-cycle people on the pavement. 6 walker types, each a real 5/6-frame side-view walk cycle (assets/people/walk_<type>_<n>.png).
// A walker's feet are planted on the PAVEMENT, which scrolls at 0.55 x world speed, and it also walks along it: the cycle phase
// advances with the distance the walker covers over the ground, so the feet never slide (no moonwalking).
const WALK_META = {"schoolboy": {"w": 96, "h": 148, "ax": 42, "n": 5, "spread": [88, 32, 32, 83, 37], "refH": 144}, "schoolgirl": {"w": 96, "h": 147, "ax": 41, "n": 5, "spread": [84, 43, 37, 88, 38], "refH": 142}, "businessman": {"w": 94, "h": 160, "ax": 41, "n": 6, "spread": [85, 78, 29, 85, 81, 76], "refH": 158}, "woman_bag": {"w": 112, "h": 161, "ax": 51, "n": 6, "spread": [102, 52, 78, 99, 65, 96], "refH": 158}, "elder": {"w": 92, "h": 163, "ax": 46, "n": 6, "spread": [79, 83, 63, 82, 80, 60], "refH": 159}, "hoodie": {"w": 105, "h": 166, "ax": 49, "n": 6, "spread": [88, 93, 68, 91, 97, 79], "refH": 162}};
const WALKER_TYPES = Object.keys(WALK_META);
const PAVE_K = 0.55;                                  // pavement scroll factor (matches the kerb ticks in _drawRoad)
const WALKER_SCALE = 0.5;                             // sprite px -> game px (hero is 0.49 but these stand further back)
// two pavement lanes (far lane: walks WITH the runner, near lane: walks TOWARDS the runner). Same-lane walkers share a
// speed, so nobody overtakes anybody and walkers never clip through each other.
const WALK_LANES = [
  { dir: +1, y: 411, z: 0.95, w: 58 },
  { dir: -1, y: 419, z: 1.04, w: 74 }
];
class AmbientPed {
  constructor(x, lane, type) {
    this.x = x; this.lane = lane; this.type = type || pick(WALKER_TYPES);
    const L = WALK_LANES[lane], M = WALK_META[this.type];
    this.dir = L.dir; this.y = L.y + rand(-1.5, 1.5); this.z = L.z;
    this.s = WALKER_SCALE * this.z;
    this.cycle = Math.max.apply(null, M.spread) * 2 * this.s;       // px of ground covered by one full walk cycle (2 steps)
    this.walk = L.w;                                               // px/s along the pavement
    this.phase = rand(0, 1);                                       // cycles
    this.t = rand(0, 6.28);
    this.vx = 0;                                                   // last on-screen velocity (tests)
  }
  update(dt, worldSpeed) {
    // screen velocity = pavement scroll (towards the left) + own walking (dir: +1 = same way as the runner)
    this.vx = -worldSpeed * PAVE_K + this.dir * this.walk;
    this.x += this.vx * dt;
    this.phase += (this.walk * dt) / this.cycle;                   // distance walked / cycle length
    this.t += dt;
  }
  draw(ctx) {
    const M = WALK_META[this.type], n = M.n, s = this.s;
    const frames = [];
    for (let i = 1; i <= n; i++) { const im = IMAGES["ppl_walk_" + this.type + "_" + i]; if (!im || !im.width) { frames.length = 0; break; } frames.push(im); }
    ctx.save();
    ctx.translate(this.x, this.y);
    // soft shadow on the pavement
    ctx.fillStyle = "rgba(0,0,0,0.20)"; ctx.beginPath(); ctx.ellipse(0, 1, 17 * this.z, 3.2 * this.z, 0, 0, 6.3); ctx.fill();
    if (frames.length) {
      const q = (((this.phase % 1) + 1) % 1) * n, i = Math.floor(q) % n, f = blendK(q - Math.floor(q)), j = (i + 1) % n;
      const bob = (0.5 - 0.5 * Math.cos(4 * Math.PI * this.phase)) * 1.1;          // a small bounce at every step
      if (this.dir < 0) ctx.scale(-1, 1);                                           // sprites face right; the near lane walks left
      ctx.translate(0, -bob);
      const w = M.w * s, h = M.h * s, ox = -M.ax * s;
      ctx.globalAlpha = Math.min(1, 2 * (1 - f)) * 0.98; ctx.drawImage(frames[i], ox, -h, w, h);
      ctx.globalAlpha = f * 0.98;                        ctx.drawImage(frames[j], ox, -h, w, h);
    } else {
      ctx.scale(0.6, 0.6);
      Vec.pedestrian(ctx, 0, 0, this.phase * 6.283, "#c1502e");
    }
    ctx.restore();
  }
}

class AmbientTaxi {
  constructor(x) { this.x = x; this.spin = 0; }
  update(dt, worldSpeed) {
    this.x -= (worldSpeed * 0.62 + 40) * dt;
    this.spin += dt * 18;
  }
  draw(ctx) {
    ctx.save();
    ctx.globalAlpha = 0.85;
    ctx.scale(0.62, 0.62);
    Vec.taxi(ctx, this.x / 0.62, 396 / 0.62, this.spin);
    ctx.restore();
  }
}

/* ---------------------------------------------------------
   WEATHER + DAY/NIGHT
--------------------------------------------------------- */
class Weather {
  constructor() {
    this.mode = "clear";
    this.timer = rand(18, 30);
    this.particles = [];
  }
  update(dt) {
    this.timer -= dt;
    if (this.timer <= 0) {
      this.mode = pick(["clear", "clear", "dust", "rain", "clear"]);
      this.timer = rand(20, 38);
    }
    const target = this.mode === "clear" ? 0 : (this.mode === "dust" ? 46 : 90);
    while (this.particles.length < target) {
      this.particles.push({
        x: rand(0, CW), y: rand(0, CH),
        vy: this.mode === "rain" ? rand(340, 480) : rand(6, 18),
        vx: this.mode === "rain" ? -rand(60,100) : -rand(20, 60),
        len: this.mode === "rain" ? rand(10, 22) : 0,
        r: this.mode === "dust" ? rand(1, 2.6) : 0
      });
    }
    while (this.particles.length > target) this.particles.pop();
    for (const p of this.particles) {
      p.x += p.vx * dt; p.y += p.vy * dt;
      if (p.y > CH) { p.y = -10; p.x = rand(0, CW); }
      if (p.x < -20) p.x = CW + 10;
    }
  }
  draw(ctx) {
    if (this.mode === "rain") {
      ctx.strokeStyle = "rgba(225,238,255,0.5)";
      ctx.lineWidth = 1.5;
      for (const p of this.particles) {
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(p.x + p.vx * 0.03, p.y + p.len);
        ctx.stroke();
      }
    } else if (this.mode === "dust") {
      ctx.fillStyle = "rgba(238,216,170,0.28)";
      for (const p of this.particles) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }
}

class DayNight {
  constructor() { this.t = DAY_CYCLE_LENGTH * 0.5; }   // phase 0 = bright midday: always start in daylight
  update(dt) { this.t = (this.t + dt) % DAY_CYCLE_LENGTH; }
  phase() {
    const f = this.t / DAY_CYCLE_LENGTH;
    return (Math.cos(f * Math.PI * 2) + 1) / 2;
  }
  isNight() { return this.phase() > 0.62; }
  skyColors() {
    const p = this.phase();
    const day    = [150, 216, 248];
    const sunset = [255, 172, 112];
    const night  = [104, 100, 170];       // soft violet dusk instead of near-black
    let top;
    if (p < 0.5) top = lerpColor(day, sunset, p / 0.5);
    else top = lerpColor(sunset, night, (p - 0.5) / 0.5);
    const bot = lerpColor(top, [255,230,180], 0.25 * (1 - p));
    return { top, bot };
  }
}
function lerpColor(a, b, t) { return [lerp(a[0],b[0],t), lerp(a[1],b[1],t), lerp(a[2],b[2],t)]; }
function rgbStr(c) { return `rgba(${c[0]|0},${c[1]|0},${c[2]|0},1)`; }

/* ---------------------------------------------------------
   KASI (TOWNSHIP) SCENERY — all procedurally drawn, no new image files.
   Every scenery piece is painted ONCE into a small offscreen canvas
   (plus an optional "lights" canvas for night) and then just blitted
   every frame, so it stays cheap on mid-range Android phones.
   Live bits (smoke, flames, washing, kids playing) are a handful of
   tiny shapes per frame.
--------------------------------------------------------- */
const Town = (function () {
  const S = Math.min(window.devicePixelRatio || 1, 1.5);   // cache resolution scale

  // One palette per painted stage: Highveld gold / Sotho blue / Zulu beadwork.
  const PALETTES = [
    { name: "Gold Hour on the Hill", far: "joburg",
      walls: ["#e0a63e", "#c9582f", "#ecd8a6", "#86b46a"], roofs: ["#6b6f73", "#8a3b2a", "#55595e"],
      zinc: ["#9aa0a6", "#b5532e", "#6f8fa3", "#7a9a6a", "#c9c3b0"],
      accent: ["#d62828", "#f7b32b", "#1d6fb8", "#2a9d4a", "#111111"], sign: "#f7b32b", ink: "#3a1a00", haze: "90,96,128" },
    { name: "Blue Blanket Streets", far: "soweto",
      walls: ["#2e78a8", "#e07a5f", "#f2cc8f", "#6fb39a"], roofs: ["#4b5563", "#7b3f3a", "#6b7280"],
      zinc: ["#8aa1b1", "#a4492f", "#5f8fa8", "#8aa38a", "#d2cdb8"],
      accent: ["#1d4e89", "#f4d35e", "#ee6c4d", "#3d9970", "#101820"], sign: "#f4d35e", ink: "#10233a", haze: "70,100,140" },
    { name: "Beaded Night Market", far: "vaal",
      walls: ["#f4f1de", "#e63946", "#2a9d8f", "#e9c46a"], roofs: ["#5a5f66", "#913232", "#464b52"],
      zinc: ["#a3a8ae", "#bb5a32", "#7a8f9f", "#6f9a7c", "#cfc7b2"],
      accent: ["#e63946", "#ffffff", "#111111", "#2a9d4a", "#1d6fb8"], sign: "#ffffff", ink: "#7a1020", haze: "110,80,120" },
    { name: "Golden City Brick", far: "cbd",
      walls: ["#b5533c", "#d9a066", "#8a8f98", "#c9c3b0"], roofs: ["#4b5563", "#6b3a2e", "#3c4048"],
      zinc: ["#9aa0a6", "#a4492f", "#6f8fa3", "#b0a78f", "#c9c3b0"],
      accent: ["#e63946", "#f4a300", "#1d6fb8", "#2a9d4a", "#111111"], sign: "#f4a300", ink: "#2a1408", haze: "120,110,120",
      w: { rank: 3, hawker: 3, spaza: 2, mural: 2, highmast: 1, glasstower: 2, tuck: 1, shisa: 1, shebeen: 1 } },
    { name: "Alex Rainbow Rows", far: "alex",
      walls: ["#e9c46a", "#2a9d8f", "#e76f51", "#f4a261"], roofs: ["#4b5563", "#8a3b2a", "#6b7280"],
      zinc: ["#8aa1b1", "#c2562e", "#5f9fa8", "#8aa38a", "#d9d1b6"],
      accent: ["#e76f51", "#2a9d8f", "#e9c46a", "#264653", "#f4a261"], sign: "#e9c46a", ink: "#264653", haze: "100,110,140",
      w: { shack: 4, rdp: 2, spaza: 3, tuck: 2, shisa: 2, hawker: 2, wash: 3, kids: 2, fire: 2, mural: 1, ndebele: 1, shebeen: 2, highmast: 1, rank: 1 } },
    { name: "Sandton Glass", far: "sandton",
      walls: ["#cfd8dc", "#90a4ae", "#eceff1", "#b0bec5"], roofs: ["#607d8b", "#455a64", "#546e7a"],
      zinc: ["#b0bec5", "#90a4ae", "#78909c", "#cfd8dc", "#eceff1"],
      accent: ["#1565c0", "#00acc1", "#ffffff", "#ffb300", "#263238"], sign: "#e3f2fd", ink: "#0d2a44", haze: "110,140,185",
      w: { glasstower: 4, highmast: 2, spaza: 1, mural: 1, hawker: 1, jacaranda: 1, bluegum: 1 } },
    { name: "Rosebank Rooftops", far: "rosebank",
      walls: ["#f2d0a4", "#d4a373", "#e9edc9", "#ccd5ae"], roofs: ["#8a3b2a", "#6b4a3a", "#7a5a4a"],
      zinc: ["#b8a99a", "#c2562e", "#8aa1b1", "#a3b18a", "#e0d6c0"],
      accent: ["#d62828", "#ffffff", "#2a9d4a", "#f7b32b", "#6a4c93"], sign: "#fff3d6", ink: "#3b2a1e", haze: "120,130,150",
      w: { hawker: 3, spaza: 2, glasstower: 1, jacaranda: 2, bluegum: 2, shisa: 1, mural: 2, rank: 1, highmast: 1 } },
    { name: "Gautrain Gateway", far: "midrand",
      walls: ["#e0e3e8", "#9fb3c8", "#f1f3f5", "#adb5bd"], roofs: ["#495057", "#343a40", "#6c757d"],
      zinc: ["#ced4da", "#adb5bd", "#868e96", "#dee2e6", "#e9ecef"],
      accent: ["#00796b", "#ffd600", "#0d47a1", "#e0e0e0", "#212121"], sign: "#ffd600", ink: "#12263a", haze: "100,125,150",
      w: { gautrain: 3, glasstower: 2, highmast: 2, bluegum: 1, spaza: 1, hawker: 1 } },
    { name: "Jacaranda City", far: "pretoria",
      walls: ["#d9b58a", "#c08457", "#e8d5b7", "#9c7a54"], roofs: ["#8a3b2a", "#6b4a3a", "#7a5a4a"],
      zinc: ["#b8a58f", "#a4492f", "#8c7aa8", "#a3b18a", "#d6cbb5"],
      accent: ["#7b2cbf", "#c77dff", "#f7b32b", "#2a9d4a", "#3c096c"], sign: "#e0aaff", ink: "#240046", haze: "130,100,160",
      w: { unionbldg: 2, jacaranda: 4, mural: 2, hawker: 2, spaza: 1, rank: 2, highmast: 1 } },
    { name: "Mamelodi Hills", far: "mamelodi",
      walls: ["#6fb39a", "#e07a5f", "#f2cc8f", "#81b29a"], roofs: ["#4b5563", "#7b3f3a", "#6b7280"],
      zinc: ["#8aa1b1", "#a4492f", "#5f8fa8", "#8aa38a", "#d2cdb8"],
      accent: ["#7b2cbf", "#f4d35e", "#ee6c4d", "#3d9970", "#101820"], sign: "#f4d35e", ink: "#2b1640", haze: "120,100,150",
      w: { rdp: 4, shack: 3, spaza: 2, kids: 3, jacaranda: 3, wash: 2, tuck: 2, fire: 2, shisa: 2, hawker: 1, ndebele: 1, highmast: 1 } },
    { name: "Runway Road", far: "airport",
      walls: ["#e5e5e5", "#ffb703", "#8ecae6", "#fb8500"], roofs: ["#495057", "#8a3b2a", "#6c757d"],
      zinc: ["#ced4da", "#c2562e", "#8aa1b1", "#a3b18a", "#e9ecef"],
      accent: ["#023e8a", "#ffb703", "#e63946", "#ffffff", "#222222"], sign: "#ffb703", ink: "#0b2447", haze: "110,140,170",
      w: { rdp: 2, highmast: 2, spaza: 1, bluegum: 3, jacaranda: 2, rank: 1, glasstower: 1, tuck: 1 } },
    { name: "Gold Reef Streets", far: "minedump",
      walls: ["#c9a227", "#b5651d", "#d8c9a3", "#8a6d3b"], roofs: ["#5c4b3a", "#7a4a2a", "#4a4038"],
      zinc: ["#a39a88", "#b5532e", "#7a8f9f", "#8a9a6a", "#cfc3a0"],
      accent: ["#d62828", "#f7b32b", "#1d6fb8", "#2a9d4a", "#111111"], sign: "#f7b32b", ink: "#2e1a00", haze: "150,120,70",
      w: { minedump: 3, rdp: 2, shack: 2, spaza: 2, shebeen: 2, rank: 2, highmast: 2, mural: 1, hawker: 1, kids: 1, tuck: 1 } },
    { name: "Cradle Country", far: "cradle",
      walls: ["#d9c4a0", "#b08968", "#e6ccb2", "#9c6644"], roofs: ["#7a5a3a", "#5c4b3a", "#8a6a4a"],
      zinc: ["#b5a58b", "#a4492f", "#7a9a6a", "#a3b18a", "#d6cbb0"],
      accent: ["#e07a1f", "#2a9d4a", "#1d6fb8", "#f7e5b0", "#3b2a1e"], sign: "#f7e5b0", ink: "#3b2a1e", haze: "150,130,90",
      w: { maropeng: 2, minedump: 1, bluegum: 3, tuck: 1, spaza: 1, fire: 2, kids: 1, shack: 1 } },
    { name: "Golden Highway Blues", far: "vaal2",
      walls: ["#3b82b8", "#f0a04b", "#f6e8b1", "#7fc4a4"], roofs: ["#4b5563", "#7b3f3a", "#6b7280"],
      zinc: ["#8aa1b1", "#b5532e", "#5f8fa8", "#8aa38a", "#d2cdb8"],
      accent: ["#1d4e89", "#f4d35e", "#ee6c4d", "#3d9970", "#101820"], sign: "#f4d35e", ink: "#10233a", haze: "90,110,150",
      w: { rdp: 3, shack: 3, spaza: 2, tuck: 2, shisa: 2, rank: 1, hawker: 2, wash: 2, kids: 1, fire: 1, shebeen: 1, highmast: 1, ndebele: 1 } }
  ];

  const defs = {};
  const cache = {};
  const haloCache = {};

  function mk(w, h) {
    const c = document.createElement("canvas");
    c.width = Math.ceil(w * S); c.height = Math.ceil(h * S);
    return c;
  }
  function rng(seed) {
    let a = (seed * 2654435761) >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function R(g, c, x, y, w, h) { g.fillStyle = c; g.fillRect(x, y, w, h); }
  function poly(g, c, pts) {
    g.fillStyle = c; g.beginPath(); g.moveTo(pts[0], pts[1]);
    for (let i = 2; i < pts.length; i += 2) g.lineTo(pts[i], pts[i + 1]);
    g.closePath(); g.fill();
  }
  function circ(g, c, x, y, r) { g.fillStyle = c; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill(); }
  function shadow(g, w) {
    g.fillStyle = "rgba(0,0,0,0.22)"; g.beginPath(); g.ellipse(0, 1, w / 2, 4, 0, 0, Math.PI * 2); g.fill();
  }
  function text(g, str, x, y, size, col, weight) {
    g.font = (weight || "bold") + " " + size + "px 'Segoe UI', Arial, sans-serif";
    g.textAlign = "center"; g.textBaseline = "middle"; g.fillStyle = col; g.fillText(str, x, y);
  }
  // corrugated-iron sheet: base colour + vertical ribs + rust streaks
  function zinc(g, x, y, w, h, col, r) {
    R(g, col, x, y, w, h);
    g.fillStyle = "rgba(0,0,0,0.17)";
    for (let xx = x + 2; xx < x + w; xx += 4) g.fillRect(xx, y, 1.2, h);
    g.fillStyle = "rgba(255,255,255,0.13)";
    for (let xx = x + 4; xx < x + w; xx += 4) g.fillRect(xx, y, 1, h);
    if (r) { g.fillStyle = "rgba(120,50,20,0.22)"; for (let i = 0; i < 2; i++) g.fillRect(x + r() * w, y, 2 + r() * 3, h * (0.3 + r() * 0.6)); }
    g.fillStyle = "rgba(0,0,0,0.25)"; g.fillRect(x, y, w, 1.2);
  }
  // a soft light: halo + bright core, painted into the glow canvas
  function lit(gl, x, y, w, h, col, haloR, coreA) {
    if (!gl) return;
    const cx = x + w / 2, cy = y + h / 2, r = haloR || Math.max(w, h) * 2.4;
    const gr = gl.createRadialGradient(cx, cy, 1, cx, cy, r);
    gr.addColorStop(0, col.replace("rgb(", "rgba(").replace(")", ",0.55)"));
    gr.addColorStop(1, col.replace("rgb(", "rgba(").replace(")", ",0)"));
    gl.fillStyle = gr; gl.fillRect(cx - r, cy - r, r * 2, r * 2);
    gl.globalAlpha = coreA === undefined ? 1 : coreA;
    gl.fillStyle = col; gl.fillRect(x, y, w, h);
    gl.globalAlpha = 1;
  }
  const WARM = "rgb(255,214,120)";
  function windowBars(g, x, y, w, h) {
    g.strokeStyle = "rgba(20,20,20,0.85)"; g.lineWidth = 1;
    for (let xx = x + w / 4; xx < x + w; xx += w / 4) { g.beginPath(); g.moveTo(xx, y); g.lineTo(xx, y + h); g.stroke(); }
    g.beginPath(); g.moveTo(x, y + h / 2); g.lineTo(x + w, y + h / 2); g.stroke();
  }
  function window_(g, gl, x, y, w, h, frame, on) {
    R(g, frame, x - 2, y - 2, w + 4, h + 4);
    R(g, "#1b2630", x, y, w, h);
    R(g, "rgba(255,255,255,0.18)", x, y, w * 0.4, h);
    windowBars(g, x, y, w, h);
    if (on) lit(gl, x, y, w, h, WARM);
  }
  function minibus(g, gl, x, body, stripe, lights) {
    g.save(); g.translate(x, 0);
    g.fillStyle = "rgba(0,0,0,0.25)"; g.beginPath(); g.ellipse(0, 1, 36, 4, 0, 0, Math.PI * 2); g.fill();
    // body (boxy Quantum-style van, nose to the right)
    poly(g, body, [-36, -6, -36, -40, 22, -44, 32, -30, 38, -22, 38, -6]);
    R(g, stripe, -36, -22, 74, 5);
    // windows
    g.fillStyle = "#26323d";
    for (let i = 0; i < 4; i++) g.fillRect(-32 + i * 13.5, -38, 11, 12);
    poly(g, "#2d3b48", [24, -37, 31, -28, 24, -28]);
    // roof rack / sign
    R(g, "#222", -22, -48, 30, 4);
    R(g, "#f2f2f2", -12, -52, 10, 4);
    // wheels
    circ(g, "#161616", -22, -5, 7); circ(g, "#161616", 24, -5, 7);
    circ(g, "#9a9a9a", -22, -5, 2.5); circ(g, "#9a9a9a", 24, -5, 2.5);
    R(g, "#d9d9d9", 35, -12, 3, 4);
    if (lights && gl) { lit(gl, 34, -15, 5, 4, "rgb(255,240,170)", 26); }
    g.restore();
  }
  const STAND = ["shop_owner", "commuter_woman", "walk_schoolboy_2", "walk_schoolgirl_3", "walk_businessman_3", "walk_woman_bag_2", "walk_elder_3", "walk_hoodie_3"];   // neutral, feet-together frames
  function pplImg(n) { const i = IMAGES["ppl_" + n]; return i && i.width ? i : null; }
  function person(g, x, col, h) {
    h = h || 26;
    // illustrated township people (cut-out sprites); the old stick figure is only the fallback
    const idx = Math.abs(Math.round(x * 3 + h * 5 + col.charCodeAt(1) * 7 + col.charCodeAt(3) * 3)) % STAND.length;
    const im = pplImg(STAND[idx]);
    if (im) {
      const hh = h * 2.1 + 14, s = hh / im.height, w = im.width * s;
      // recorded, then drawn LIVE every frame by drawProp() with a breathing / swaying idle loop
      if (g.__ppl) g.__ppl.push({ n: STAND[idx], x, hh, flip: Math.round(x) % 2 === 0, mode: "breath", ph: (x * 0.37 + h) % 6.28 });
      else { g.save(); g.translate(x, 0); if (Math.round(x) % 2 === 0) g.scale(-1, 1); g.drawImage(im, -w / 2, -hh, w, hh); g.restore(); }
      return;
    }
    circ(g, "#3b2a1e", x, -h - 4, 3.6);
    R(g, col, x - 3.5, -h, 7, h * 0.5);
    R(g, "#222", x - 3, -h * 0.5, 2.6, h * 0.5);
    R(g, "#222", x + 0.6, -h * 0.5, 2.6, h * 0.5);
  }

  /* ------------------ sprite definitions ------------------ */
  defs.rdp = { w: 150, h: 112, glow: true, draw(g, gl, P, r, v) {
    shadow(g, 140);
    const wall = P.walls[v % P.walls.length], bw = 92 + (v % 2) * 14, bh = 48;
    // JoJo water tank on a stand
    R(g, "#6d5a45", bw / 2 + 16, -22, 3, 22); R(g, "#6d5a45", bw / 2 + 32, -22, 3, 22);
    R(g, "#1a1d21", bw / 2 + 12, -48, 26, 28);
    g.fillStyle = "#1a1d21"; g.beginPath(); g.ellipse(bw / 2 + 25, -48, 13, 4, 0, 0, Math.PI * 2); g.fill();
    R(g, "rgba(255,255,255,0.15)", bw / 2 + 15, -46, 4, 24);
    // house
    R(g, wall, -bw / 2, -bh, bw, bh);
    R(g, "rgba(0,0,0,0.13)", -bw / 2, -9, bw, 9);
    R(g, "rgba(255,255,255,0.10)", -bw / 2, -bh, bw, 3);
    poly(g, P.roofs[v % P.roofs.length], [-bw / 2 - 6, -bh, 0, -bh - 24, bw / 2 + 6, -bh]);
    g.strokeStyle = "rgba(0,0,0,0.25)"; g.lineWidth = 1;
    for (let i = 1; i < 5; i++) { g.beginPath(); g.moveTo(-bw / 2 - 6 + i * 4, -bh - i * 0); g.lineTo(-bw / 2 + 6 + i * 3, -bh - 5 * i / 2 - 1); g.stroke(); }
    // door + windows
    R(g, P.accent[v % 4], -8, -30, 16, 30); R(g, "rgba(0,0,0,0.25)", -8, -30, 16, 2);
    text(g, "43", 0, -22, 8, "#fff");
    window_(g, gl, -bw / 2 + 9, -bh + 12, 20, 16, "#f1ece0", true);
    window_(g, gl, bw / 2 - 29, -bh + 12, 20, 16, "#f1ece0", r() > 0.35);
    // DStv-style dish
    g.fillStyle = "#e6e6e6"; g.beginPath(); g.ellipse(bw / 2 - 6, -bh + 6, 7, 5, -0.5, 0, Math.PI * 2); g.fill();
    R(g, "#555", bw / 2 - 7, -bh + 8, 1.6, 8);
    // low yard fence
    g.strokeStyle = "#5c4b3a"; g.lineWidth = 2;
    for (let x = -bw / 2 - 14; x <= bw / 2 + 4; x += 7) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, -14); g.stroke(); }
    g.strokeStyle = "rgba(90,90,90,0.9)"; g.lineWidth = 1;
    g.beginPath(); g.moveTo(-bw / 2 - 14, -12); g.lineTo(bw / 2 + 4, -12); g.moveTo(-bw / 2 - 14, -5); g.lineTo(bw / 2 + 4, -5); g.stroke();
  }};

  defs.shack = { w: 124, h: 100, glow: true, draw(g, gl, P, r, v) {
    shadow(g, 110);
    const z = P.zinc;
    // body made from mismatched zinc sheets
    let x = -48;
    const widths = [18, 22, 16, 24, 20];
    for (let i = 0; i < widths.length; i++) {
      const hh = 46 + ((i * 7 + v * 3) % 12);
      zinc(g, x, -hh, widths[i], hh, z[(i + v) % z.length], r);
      x += widths[i];
    }
    // sloped roof of sheets + tyres + bricks
    poly(g, "#7d838a", [-56, -52, 56, -62, 54, -57, -54, -47]);
    for (let i = 0; i < 12; i++) { g.fillStyle = i % 2 ? "rgba(0,0,0,0.2)" : "rgba(255,255,255,0.15)"; g.fillRect(-54 + i * 9, -61 + i * 0.4, 1.4, 12); }
    g.strokeStyle = "#1c1c1c"; g.lineWidth = 3;
    g.beginPath(); g.ellipse(-30, -57, 8, 3.4, -0.05, 0, Math.PI * 2); g.stroke();
    g.beginPath(); g.ellipse(18, -60, 8, 3.4, -0.05, 0, Math.PI * 2); g.stroke();
    R(g, "#a0522d", 36, -64, 8, 4); R(g, "#a0522d", 39, -68, 8, 4);
    // chimney pipe with smoke stain
    R(g, "#444", -42, -76, 5, 20); R(g, "#2d2d2d", -44, -78, 9, 3);
    // door and cut-out window with curtain
    R(g, "#6b4a2b", -6, -34, 17, 34);
    g.strokeStyle = "rgba(0,0,0,0.35)"; g.lineWidth = 1;
    for (let i = 1; i < 4; i++) { g.beginPath(); g.moveTo(-6 + i * 4.2, -34); g.lineTo(-6 + i * 4.2, 0); g.stroke(); }
    R(g, "#1b2630", 22, -34, 15, 13); R(g, P.accent[(v + 1) % 4], 22, -34, 6, 13);
    lit(gl, 29, -33, 7, 11, WARM, 24);
    // illegal wire dropping from the pole
    g.strokeStyle = "rgba(10,10,10,0.7)"; g.lineWidth = 1;
    g.beginPath(); g.moveTo(52, -70); g.quadraticCurveTo(64, -48, 58, -36); g.stroke();
    // paint bucket / drum
    R(g, "#2a6fb0", -58, -16, 9, 16);
    if (v % 2) { g.fillStyle = "#e6e6e6"; g.beginPath(); g.ellipse(46, -78, 7, 4, -0.4, 0, Math.PI * 2); g.fill(); R(g, "#555", 45, -76, 1.6, 8); }
  }};

  const SPAZA_NAMES = ["THEMBA'S SPAZA", "MAMA NOZI SPAZA", "SIYABONGA SPAZA", "KWA-MOKOENA TUCK", "GAUTENG SPAZA", "JOZI SPAZA", "EGOLI TUCK SHOP"];
  defs.spaza = { w: 190, h: 124, glow: true, draw(g, gl, P, r, v) {
    shadow(g, 176);
    const wall = P.walls[(v + 1) % P.walls.length], bw = 150, bh = 78;
    R(g, wall, -bw / 2, -bh, bw, bh);
    R(g, "rgba(0,0,0,0.12)", -bw / 2, -10, bw, 10);
    R(g, "#4a4a4a", -bw / 2 - 3, -bh - 6, bw + 6, 7);                  // parapet
    // painted sign band
    R(g, P.sign, -bw / 2 + 6, -bh + 2, bw - 12, 22);
    R(g, "rgba(0,0,0,0.25)", -bw / 2 + 6, -bh + 22, bw - 12, 2);
    text(g, SPAZA_NAMES[v % SPAZA_NAMES.length], 0, -bh + 13, 12, P.ink, "900");
    lit(gl, -bw / 2 + 8, -bh + 4, bw - 16, 18, "rgb(255,230,150)", 70, 0.0);
    // striped awning
    for (let i = 0; i < 10; i++) R(g, i % 2 ? "#fff" : P.accent[0], -bw / 2 + 12 + i * 12.6, -bh + 26, 12.6, 12);
    // shop front: counter window behind security gate
    R(g, "#1d2a33", -34, -50, 68, 38);
    R(g, "#caa56b", -34, -50, 68, 3);
    for (let i = 0; i < 6; i++) for (let j = 0; j < 2; j++) R(g, P.accent[(i + j + v) % 5], -30 + i * 11, -44 + j * 14, 8, 9);
    lit(gl, -33, -49, 66, 36, "rgb(255,205,110)", 62, 0.3);
    g.strokeStyle = "#111"; g.lineWidth = 1.2;
    for (let x = -34; x <= 34; x += 6) { g.beginPath(); g.moveTo(x, -50); g.lineTo(x, -12); g.stroke(); }
    for (let y = -50; y <= -12; y += 9.5) { g.beginPath(); g.moveTo(-34, y); g.lineTo(34, y); g.stroke(); }
    // painted advert panels either side
    R(g, "#d62828", -bw / 2 + 8, -52, 34, 40); text(g, "ICE", -bw / 2 + 25, -42, 11, "#fff", "900"); text(g, "COLD", -bw / 2 + 25, -30, 11, "#fff", "900");
    R(g, "#1d6fb8", bw / 2 - 42, -52, 34, 40); text(g, "AIR", bw / 2 - 25, -42, 11, "#ffe14d", "900"); text(g, "TIME", bw / 2 - 25, -30, 11, "#ffe14d", "900");
    // crates of cooldrink out front
    for (let i = 0; i < 2; i++) {
      R(g, "#b8321f", 40 + i * 15, -14, 14, 14);
      for (let j = 0; j < 3; j++) { R(g, ["#3b2314", "#e8b500", "#2d7a3e"][(j + i) % 3], 42 + i * 15 + j * 4, -20, 3, 7); }
    }
    person(g, -50, P.accent[1], 28);
  }};

  defs.tuck = { w: 140, h: 92, glow: true, draw(g, gl, P, r, v) {
    shadow(g, 130);
    const col = P.accent[v % 4];
    R(g, col, -56, -56, 112, 56);
    g.fillStyle = "rgba(0,0,0,0.2)"; for (let x = -54; x < 56; x += 5) g.fillRect(x, -56, 1.5, 56);
    g.fillStyle = "rgba(255,255,255,0.15)"; for (let x = -52; x < 56; x += 5) g.fillRect(x, -56, 1, 56);
    R(g, "rgba(0,0,0,0.3)", -56, -57, 112, 2);
    // hatch
    R(g, "#1d2a33", -34, -44, 54, 24);
    lit(gl, -33, -43, 52, 22, "rgb(255,200,100)", 54, 0.4);
    for (let i = 0; i < 7; i++) R(g, P.accent[(i + v) % 5], -32 + i * 7.3, -42, 5, 8);   // hanging chips packets
    // prop-up flap
    poly(g, P.sign, [-40, -46, 26, -46, 30, -52, -44, -52]);
    R(g, "#444", -40, -46, 1.8, 26); R(g, "#444", 24, -46, 1.8, 26);
    text(g, "TUCK SHOP", 0, -60 + 4, 11, P.ink, "900");
    R(g, "#fff", -52, -30, 14, 24); text(g, "BREAD", -45, -24, 5, "#a00", "900"); text(g, "KOTA", -45, -15, 5.4, "#a00", "900");
    R(g, "#6b4a2b", 28, -42, 22, 42); R(g, "#222", 33, -22, 2, 3);
    // bench & kid
    R(g, "#7a5a3a", -50, -8, 24, 3); R(g, "#7a5a3a", -48, -8, 2, 8); R(g, "#7a5a3a", -29, -8, 2, 8);
    person(g, 58, P.accent[2], 22);
  }};

  defs.shisa = { w: 196, h: 116, glow: true, live: true, draw(g, gl, P, r, v) {
    shadow(g, 176);
    // shade-cloth / zinc roof on four poles
    R(g, "#5a4630", -84, -72, 3.4, 72); R(g, "#5a4630", 78, -72, 3.4, 72);
    R(g, "#5a4630", -30, -66, 3, 66); R(g, "#5a4630", 30, -66, 3, 66);
    poly(g, "#7d838a", [-96, -66, 96, -78, 96, -72, -96, -60]);
    g.fillStyle = "rgba(0,0,0,0.18)"; for (let x = -94; x < 96; x += 5) g.fillRect(x, -77 + (x + 96) * 0.0, 1.2, 14);
    // hand-painted board
    R(g, "#f4efe2", -60, -56, 122, 20);
    g.strokeStyle = P.accent[0]; g.lineWidth = 2; g.strokeRect(-58, -54, 118, 16);
    text(g, "SHISANYAMA", 0, -46, 13, P.accent[0], "900");
    // drum braai (left)
    R(g, "#3a3a3a", -76, -22, 3, 22); R(g, "#3a3a3a", -52, -22, 3, 22);
    R(g, "#2a2a2a", -80, -34, 34, 14);
    lit(gl, -76, -34, 26, 4, "rgb(255,120,40)", 38);
    g.strokeStyle = "#999"; g.lineWidth = 1;
    for (let x = -78; x < -46; x += 4) { g.beginPath(); g.moveTo(x, -36); g.lineTo(x, -34); g.stroke(); }
    // table with plastic chairs
    R(g, "#d9d2c0", 0, -22, 54, 4); R(g, "#6b6b6b", 6, -18, 2.4, 18); R(g, "#6b6b6b", 46, -18, 2.4, 18);
    R(g, "#e63946", 8, -26, 8, 3); R(g, "#2a9d4a", 24, -27, 8, 4); R(g, "#f7b32b", 38, -26, 8, 3);  // pap, chakalaka, meat
    R(g, "#e63946", -14, -20, 12, 3); R(g, "#e63946", -14, -20, 2.4, 20); R(g, "#e63946", -4, -20, 2.4, 20);
    R(g, "#1d6fb8", 62, -20, 12, 3); R(g, "#1d6fb8", 62, -20, 2.4, 20); R(g, "#1d6fb8", 72, -20, 2.4, 20);
    person(g, 20, P.accent[3], 28);
    // bulbs
    for (let i = 0; i < 5; i++) { const bx = -66 + i * 33; circ(g, "#ffe9a0", bx, -64 + (i % 2) * 2, 2.4); lit(gl, bx - 2, -66 + (i % 2) * 2, 4, 4, "rgb(255,225,140)", 22); }
  }, liveDraw(g, t, P, v) {
    // flames, coals and rising smoke from the drum braai
    const fl = 3 + Math.sin(t * 17) * 1.4;
    g.fillStyle = "rgba(255,130,30,0.9)"; g.beginPath(); g.moveTo(-72, -36); g.quadraticCurveTo(-66, -36 - fl * 2.4, -60, -36); g.fill();
    g.fillStyle = "rgba(255,220,90,0.9)"; g.beginPath(); g.moveTo(-68, -36); g.quadraticCurveTo(-63, -36 - fl * 1.5, -58, -36); g.fill();
    for (let i = 0; i < 6; i++) {
      const ph = (t * 0.32 + i / 6) % 1;
      const px = -64 + ph * 26 + Math.sin(t * 2 + i) * 4, py = -40 - ph * 78, rr = 3 + ph * 13;
      g.fillStyle = "rgba(190,190,190," + ((1 - ph) * 0.34).toFixed(3) + ")";
      g.beginPath(); g.arc(px, py, rr, 0, Math.PI * 2); g.fill();
    }
  }, liveGlow(g, t, night) {
    const a = (0.5 + 0.15 * Math.sin(t * 13)) * (0.4 + 0.6 * night);
    const gr = g.createRadialGradient(-62, -34, 2, -62, -34, 46);
    gr.addColorStop(0, "rgba(255,140,50," + a.toFixed(3) + ")"); gr.addColorStop(1, "rgba(255,90,20,0)");
    g.fillStyle = gr; g.fillRect(-110, -80, 96, 90);
  }};

  defs.rank = { w: 268, h: 104, glow: true, draw(g, gl, P, r, v) {
    shadow(g, 250);
    // shelter + sign
    R(g, "#444", -118, -70, 3, 70); R(g, "#1d4e89", -134, -84, 38, 22);
    text(g, "TAXI", -115, -78, 9, "#fff", "900"); text(g, "RANK", -115, -68, 9, "#ffe14d", "900");
    lit(gl, -134, -84, 38, 22, "rgb(120,170,255)", 40, 0.0);
    poly(g, "#fff", [-132, -58, -110, -58, -102, -54, -110, -50, -132, -50]);
    const bodies = ["#f2f2ee", "#f6f1e0", "#e9eef2"];
    minibus(g, gl, -66, bodies[v % 3], P.accent[2], true);
    minibus(g, gl, 8, bodies[(v + 1) % 3], P.accent[0], false);
    minibus(g, gl, 82, bodies[(v + 2) % 3], P.accent[1], true);
    // queue of commuters & a marshal in hi-vis
    person(g, -92, P.accent[1], 26); person(g, -86, "#333", 24); person(g, -80, P.accent[3], 27);
    person(g, 118, "#ff9f1c", 28);
    R(g, "#ff9f1c", 114.5, -22, 7, 2);
    // kerb stones
    R(g, "#999", -124, -2, 246, 3);
  }};

  defs.hawker = { w: 128, h: 104, glow: true, draw(g, gl, P, r, v) {
    shadow(g, 112);
    const st = pplImg("hawker_stall"), vd = pplImg("vendor_crate");
    // big umbrella
    const cols = [P.accent[0], "#ffffff", P.accent[2], "#ffffff", P.accent[1], "#ffffff"];
    for (let i = 0; i < 6; i++) {
      g.fillStyle = cols[i]; g.beginPath(); g.moveTo(-14, -98);
      g.lineTo(-66 + i * 17.3, -72); g.lineTo(-66 + (i + 1) * 17.3, -72); g.closePath(); g.fill();
    }
    R(g, "#444", -15, -98, 2, 56);
    if (st) { g.__ppl.push({ n: "hawker_stall", x: -14, hh: 80, flip: false, mode: "gesture", ph: 0.6 }); }
    else { R(g, "#7a5a3a", -50, -26, 72, 4); R(g, "#6b4a2b", -46, -22, 3, 22); R(g, "#6b4a2b", 16, -22, 3, 22); for (let i = 0; i < 6; i++) circ(g, "#ff8c1a", -42 + i * 5.2, -29, 3.2); circ(g, "#3b2a1e", -14, -50, 5); R(g, P.accent[3], -20, -46, 12, 18); }
    if (vd) { g.__ppl.push({ n: "vendor_crate", x: 34, hh: 54, flip: false, mode: "breath", ph: 2.1 }); }
    lit(gl, -16, -74, 4, 4, "rgb(255,230,150)", 40);
  }};

  const MURAL_WORDS = ["UBUNTU", "AMANDLA", "GAUTENG", "HUSTLE", "JOZI", "UMUNTU"];
  defs.mural = { w: 214, h: 112, glow: false, draw(g, gl, P, r, v) {
    shadow(g, 200);
    const w = 190, h = 74;
    R(g, "#cfc8b8", -w / 2, -h, w, h);
    // sky/sun gradient panel
    const gr = g.createLinearGradient(0, -h + 8, 0, -16);
    gr.addColorStop(0, P.accent[1] === "#ffffff" ? "#ffd166" : P.accent[1]); gr.addColorStop(1, P.accent[0]);
    g.fillStyle = gr; g.fillRect(-w / 2 + 10, -h + 10, w - 20, h - 28);
    circ(g, "rgba(255,255,255,0.8)", 48, -48, 14);
    // rolling hills
    g.fillStyle = P.accent[3]; g.beginPath(); g.moveTo(-w / 2 + 10, -18);
    g.quadraticCurveTo(-40, -44, 10, -26); g.quadraticCurveTo(50, -38, w / 2 - 10, -18); g.closePath(); g.fill();
    // Ubuntu: row of linked silhouettes
    for (let i = 0; i < 5; i++) {
      const px = -52 + i * 24, ph = 24 + (i % 2) * 5;
      circ(g, "#151515", px, -34 - ph + 4, 4.2); R(g, "#151515", px - 4, -34 - ph + 8, 8, ph - 4);
      g.strokeStyle = "#151515"; g.lineWidth = 2.2; g.beginPath(); g.moveTo(px, -34 - ph + 12); g.lineTo(px + 12, -34 - ph + 18); g.stroke();
    }
    // lettering
    g.lineWidth = 3; g.strokeStyle = "#101010"; g.font = "900 17px 'Segoe UI', Arial, sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
    const word = MURAL_WORDS[v % MURAL_WORDS.length];
    g.strokeText(word, -26, -h + 22); g.fillStyle = "#fff"; g.fillText(word, -26, -h + 22);
    // Ndebele-style border (triangles) top and bottom
    for (let i = 0; i < 19; i++) {
      const c = P.accent[i % 5];
      poly(g, c, [-w / 2 + i * 10, -h, -w / 2 + i * 10 + 10, -h, -w / 2 + i * 10 + 5, -h + 8]);
      poly(g, c, [-w / 2 + i * 10, 0, -w / 2 + i * 10 + 10, 0, -w / 2 + i * 10 + 5, -8]);
    }
    // wall cap + razor-wire squiggle
    R(g, "#8d8577", -w / 2 - 3, -h - 4, w + 6, 5);
    g.strokeStyle = "rgba(60,60,60,0.9)"; g.lineWidth = 1; g.beginPath();
    for (let x = -w / 2; x < w / 2; x += 6) { g.moveTo(x, -h - 4); g.quadraticCurveTo(x + 3, -h - 14, x + 6, -h - 4); }
    g.stroke();
    // pillar, tuft of grass
    R(g, "#a79f8f", -w / 2 - 4, -h - 4, 7, h + 4); R(g, "#a79f8f", w / 2 - 3, -h - 4, 7, h + 4);
  }};

  defs.ndebele = { w: 136, h: 104, glow: true, draw(g, gl, P, r, v) {
    shadow(g, 124);
    const bw = 104, bh = 64;
    R(g, "#fbf7ee", -bw / 2, -bh, bw, bh);
    g.lineWidth = 2; g.strokeStyle = "#111";
    // geometric painted bands
    for (let row = 0; row < 3; row++) {
      const y0 = -bh + 4 + row * 14;
      for (let i = 0; i < 9; i++) {
        const x0 = -bw / 2 + 4 + i * 11;
        poly(g, P.accent[(i + row * 2) % 5], row % 2 ? [x0, y0, x0 + 11, y0, x0 + 5.5, y0 + 11] : [x0, y0 + 11, x0 + 11, y0 + 11, x0 + 5.5, y0]);
      }
    }
    g.strokeRect(-bw / 2, -bh, bw, bh);
    R(g, P.accent[1] === "#ffffff" ? P.accent[0] : P.accent[1], -bw / 2 - 4, -bh - 6, bw + 8, 7);
    // stepped gable
    for (let i = 0; i < 4; i++) R(g, i % 2 ? P.accent[3] : P.accent[2], -26 + i * 6, -bh - 6 - (i + 1) * 5, 52 - i * 12, 5);
    // door arch + windows
    R(g, "#3a2a1c", -8, -28, 16, 28);
    g.fillStyle = P.accent[0]; g.beginPath(); g.arc(0, -28, 8, Math.PI, 0); g.fill();
    window_(g, gl, -bw / 2 + 8, -bh + 44, 18, 14, P.accent[2], true);
    window_(g, gl, bw / 2 - 26, -bh + 44, 18, 14, P.accent[2], true);
    // pot plants
    R(g, "#a0522d", bw / 2 + 4, -10, 9, 10); circ(g, "#2a8a3a", bw / 2 + 8.5, -16, 6);
  }};

  defs.shebeen = { w: 170, h: 100, glow: true, live: true, glowPulse: true, draw(g, gl, P, r, v) {
    shadow(g, 156);
    const bw = 104, bh = 54;
    R(g, P.walls[(v + 2) % 4], -bw / 2, -bh, bw, bh);
    R(g, "rgba(0,0,0,0.13)", -bw / 2, -9, bw, 9);
    R(g, P.roofs[1], -bw / 2 - 5, -bh - 7, bw + 10, 8);
    R(g, "#111", -bw / 2 + 8, -bh + 4, 62, 18); text(g, "KWA-MZIZI TAVERN", -bw / 2 + 39, -bh + 13, 7.4, "#ffd23f", "900");
    lit(gl, -bw / 2 + 10, -bh + 6, 58, 14, "rgb(255,210,90)", 46, 0.0);
    R(g, "#2b1d14", -14, -32, 24, 32);
    window_(g, gl, bw / 2 - 30, -bh + 14, 22, 18, "#f1ece0", true);
    // loudspeaker stack
    R(g, "#141414", bw / 2 + 6, -34, 20, 34); circ(g, "#2a2a2a", bw / 2 + 16, -24, 6); circ(g, "#2a2a2a", bw / 2 + 16, -8, 6);
    circ(g, "#444", bw / 2 + 16, -24, 2); circ(g, "#444", bw / 2 + 16, -8, 2);
    // beer crates and plastic chairs
    for (let i = 0; i < 3; i++) R(g, "#d98e04", -bw / 2 - 28 + i * 9, -9, 9, 9);
    R(g, "#d98e04", -bw / 2 - 24, -18, 9, 9);
    R(g, "#e63946", -bw / 2 + 4, -14, 10, 3); R(g, "#e63946", -bw / 2 + 4, -14, 2, 14); R(g, "#e63946", -bw / 2 + 12, -14, 2, 14);
    // festoon lights (static bulbs + glow)
    g.strokeStyle = "rgba(20,20,20,0.7)"; g.lineWidth = 1; g.beginPath();
    g.moveTo(-bw / 2 - 18, -bh - 4); g.quadraticCurveTo(0, -bh + 14, bw / 2 + 24, -bh - 4); g.stroke();
    const cols = ["rgb(255,70,70)", "rgb(255,214,60)", "rgb(80,220,110)", "rgb(80,160,255)", "rgb(255,120,230)"];
    for (let i = 0; i <= 8; i++) {
      const tt = i / 8, bx = lerp(-bw / 2 - 18, bw / 2 + 24, tt), by = (1 - tt) * (1 - tt) * (-bh - 4) + 2 * tt * (1 - tt) * (-bh + 14) + tt * tt * (-bh - 4);
      circ(g, cols[i % 5], bx, by + 3, 2.6);
      lit(gl, bx - 2, by + 1, 4, 4, cols[i % 5], 20);
    }
  }, liveDraw(g, t, P, v) {
    // dancing silhouettes by the door
    const b = Math.abs(Math.sin(t * 7)) * 3;
    for (let i = 0; i < 2; i++) {
      const px = -40 - i * 14 + 6 * i, bb = Math.abs(Math.sin(t * 7 + i * 1.7)) * 3;
      circ(g, "#181818", px, -30 - bb, 3.4); R(g, "#181818", px - 3, -27 - bb, 6, 14);
      g.strokeStyle = "#181818"; g.lineWidth = 1.8; g.beginPath();
      g.moveTo(px - 3, -25 - bb); g.lineTo(px - 8, -33 - bb + Math.sin(t * 7 + i) * 3); g.moveTo(px + 3, -25 - bb); g.lineTo(px + 8, -33 - bb - Math.sin(t * 7 + i) * 3); g.stroke();
      R(g, "#181818", px - 3, -13 - bb, 2.4, 13 + bb); R(g, "#181818", px + 1, -13 - bb, 2.4, 13 + bb);
    }
  }};

  defs.wash = { w: 176, h: 92, glow: false, live: true, draw(g, gl, P, r, v) {
    // two leaning poles with a rope
    g.strokeStyle = "#5a4630"; g.lineWidth = 3;
    g.beginPath(); g.moveTo(-76, 0); g.lineTo(-80, -68); g.moveTo(76, 0); g.lineTo(80, -66); g.stroke();
    g.strokeStyle = "rgba(240,240,240,0.9)"; g.lineWidth = 1;
    g.beginPath(); g.moveTo(-80, -66); g.quadraticCurveTo(0, -48, 80, -64); g.stroke();
    R(g, "#a0522d", -90, -10, 10, 10);
  }, liveDraw(g, t, P, v) {
    const ropeY = (x) => { const u = (x + 80) / 160; return (1 - u) * (1 - u) * -66 + 2 * u * (1 - u) * -48 + u * u * -64; };
    const items = [
      { x: -62, w: 14, h: 20, c: P.accent[0] }, { x: -44, w: 12, h: 26, c: "#2e5ca8" }, { x: -26, w: 24, h: 30, c: P.accent[1] === "#ffffff" ? "#e6b800" : P.accent[1], blanket: true },
      { x: 6, w: 14, h: 20, c: "#f4f4f4" }, { x: 26, w: 12, h: 27, c: "#3a3a3a" }, { x: 46, w: 14, h: 18, c: P.accent[3] }
    ];
    items.forEach((it, i) => {
      const sway = Math.sin(t * 2.2 + i * 1.3) * 0.12, y0 = ropeY(it.x);
      g.save(); g.translate(it.x, y0); g.rotate(sway);
      g.fillStyle = it.c; g.fillRect(-it.w / 2, 0, it.w, it.h);
      if (it.blanket) {   // Basotho-blanket style stripes
        g.fillStyle = "rgba(0,0,0,0.55)"; g.fillRect(-it.w / 2, 6, it.w, 2.5); g.fillRect(-it.w / 2, 14, it.w, 2.5);
        g.fillStyle = "rgba(255,255,255,0.75)"; g.fillRect(-it.w / 2 + 3, 0, 2.4, it.h);
      } else { g.fillStyle = "rgba(0,0,0,0.12)"; g.fillRect(0, 0, it.w / 2, it.h); }
      g.restore();
    });
  }};

  defs.kids = { w: 150, h: 80, glow: false, live: true, draw(g, gl, P, r, v) {
    shadow(g, 120);
    // crate goal-posts
    R(g, "#8a6a3a", -66, -18, 10, 18); R(g, "#8a6a3a", 56, -18, 10, 18);
  }, liveDraw(g, t, P, v) {
    const kk = pplImg("kid_kick"), kd = pplImg("kid_dribble"), bl = pplImg("ball");
    if (kk && kd) {
      // Two kids pass a football. Every 2.4 s the kicker kicks (kick pose, ball released from the boot), the ball flies in an
      // arc (parabola), lands, bounces once, rolls to the other kid's feet - then they swap roles.
      const XA = -36, XB = 36, HALF = 2.4, KICK = 0.55, FLY = 0.9, G = -4.5;
      const k = Math.floor(t / HALF), u = t - k * HALF, aKicks = (k % 2) === 0;
      const kx = aKicks ? XA : XB, rx = aKicks ? XB : XA, dir = aKicks ? 1 : -1;
      const rel = { x: kx + dir * 20, y: -33 }, land = { x: rx - dir * 14, y: G };
      let bx, by, rot = 0;
      if (u >= KICK - 0.06 && u < KICK) {                // the boot swings through: the ball is lifted to the release point
        const f = (u - (KICK - 0.06)) / 0.06;
        bx = lerp(kx + dir * 9, rel.x, f); by = lerp(G, rel.y, f * f); rot = u * 9 * dir;
      } else if (u < KICK) {                             // dribbling at the kicker's feet
        bx = kx + dir * (9 + 3 * Math.sin(u * 11)); by = G - Math.abs(Math.sin(u * 11)) * 4.5; rot = u * 9 * dir;
      } else if (u < KICK + FLY) {                       // flight: straight line in x, parabola in y
        const f = (u - KICK) / FLY;
        bx = lerp(rel.x, land.x, f); by = lerp(rel.y, land.y, f) - 4 * 20 * f * (1 - f); rot = (9 * KICK + (u - KICK) * 14) * dir;
      } else if (u < KICK + FLY + 0.34) {                // one lower bounce
        const f = (u - KICK - FLY) / 0.34;
        bx = land.x + dir * 7 * f; by = G - 4 * 7 * f * (1 - f); rot = (9 * KICK + FLY * 14 + (u - KICK - FLY) * 9) * dir;
      } else {                                           // rolls the last bit to the receiver
        const f = Math.min(1, Math.max(0, (u - KICK - FLY - 0.34) / (HALF - KICK - FLY - 0.34)));
        bx = lerp(land.x + dir * 7, rx - dir * 9, f * (2 - f)); by = G; rot = (9 * KICK + FLY * 14 + 3 + f * 5) * dir;
      }
      const kicking = u >= KICK - 0.06 && u < KICK + 0.26;
      const kid = (x, face, pose, hh, bounce) => { const im = pose ? kk : kd, s = hh / im.height, w = im.width * s;
        g.save(); g.translate(x, -bounce); if (face < 0) g.scale(-1, 1); g.drawImage(im, -w / 2, -hh, w, hh); g.restore(); };
      const idleHop = (ph) => Math.max(0, Math.sin(t * 6.1 + ph)) * 1.6;
      kid(XA, 1, aKicks && kicking, aKicks && kicking ? 62 : 56, aKicks ? 0 : idleHop(0));
      kid(XB, -1, !aKicks && kicking, !aKicks && kicking ? 62 : 56, aKicks ? idleHop(1.7) : 0);
      // ball shadow on the ground shrinks with height
      g.fillStyle = "rgba(0,0,0," + (0.22 / (1 + Math.max(0, -by - 4.5) * 0.08)).toFixed(3) + ")"; g.beginPath(); g.ellipse(bx, 0.5, 4.6, 1.5, 0, 0, 6.3); g.fill();
      if (bl) { g.save(); g.translate(bx, by); g.rotate(rot); g.drawImage(bl, -4.8, -4.8, 9.6, 9.6); g.restore(); }
      else { g.save(); g.translate(bx, by); g.rotate(rot); circ(g, "#f4f4f4", 0, 0, 4.6); g.fillStyle = "#111"; g.fillRect(-1.4, -1.4, 2.8, 2.8); g.restore(); }
      return;
    }
    function kid(x, col, ph) {
      const sw = Math.sin(t * 9 + ph) * 5;
      circ(g, "#3b2a1e", x, -34, 3.8); R(g, col, x - 3.8, -30, 7.6, 12);
      g.strokeStyle = "#222"; g.lineWidth = 2.4; g.lineCap = "round";
      g.beginPath(); g.moveTo(x, -18); g.lineTo(x + sw, 0); g.moveTo(x, -18); g.lineTo(x - sw, 0); g.stroke();
      g.strokeStyle = col; g.lineWidth = 2;
      g.beginPath(); g.moveTo(x, -28); g.lineTo(x - sw, -20); g.moveTo(x, -28); g.lineTo(x + sw, -20); g.stroke();
    }
    const u = (t * 0.9) % 2, bx = -38 + (u < 1 ? u : 2 - u) * 76, by = -Math.abs(Math.sin(t * 6.3)) * 16 - 3;
    kid(-48 + Math.sin(t * 1.8) * 6, P.accent[0], 0);
    kid(46 + Math.cos(t * 1.8) * 6, P.accent[2], 1.5);
    kid(0 + Math.sin(t * 0.9) * 8, P.accent[3], 3);
    // the ball (soccer pattern)
    g.save(); g.translate(bx, by); g.rotate(t * 8);
    circ(g, "#f4f4f4", 0, 0, 4.6); g.fillStyle = "#111"; g.fillRect(-1.4, -1.4, 2.8, 2.8);
    g.fillRect(-4, -0.6, 1.6, 1.2); g.fillRect(2.4, -0.6, 1.6, 1.2); g.restore();
    // spinning kid with arms out (far right)
    const sp = Math.sin(t * 5);
    g.save(); g.translate(76, 0); g.scale(Math.abs(sp) * 0.6 + 0.4, 1);
    circ(g, "#3b2a1e", 0, -32, 3.8); R(g, "#ff9f1c", -3.8, -28, 7.6, 12);
    R(g, "#222", -3, -16, 6, 16); R(g, "#ff9f1c", -12, -27, 24, 2.4);
    g.restore();
  }};

  defs.fire = { w: 96, h: 100, glow: false, live: true, draw(g, gl, P, r, v) {
    shadow(g, 56);
    R(g, "#6b3a22", -10, -28, 20, 28);
    g.fillStyle = "rgba(0,0,0,0.3)"; for (let y = -26; y < 0; y += 6) g.fillRect(-10, y, 20, 1.4);
    R(g, "#222", -10, -29, 20, 3);
    person(g, -24, P.accent[2], 28); person(g, 24, P.accent[0], 30);
    g.strokeStyle = "#3b2a1e"; g.lineWidth = 2; g.beginPath();
    g.moveTo(-24, -20); g.lineTo(-14, -26); g.moveTo(24, -22); g.lineTo(14, -26); g.stroke();
    const bm = pplImg("braai_man");
    if (bm) { g.clearRect(-60, -110, 120, 112); shadow(g, 56); const s = 84 / bm.height; g.__ppl.length = 0; g.__ppl.push({ n: "braai_man", x: -bm.width * s * 0.66 + bm.width * s / 2, hh: 84, flip: false, mode: "work", ph: 0 }); }
  }, liveDraw(g, t, P, v) {
    if (pplImg("braai_man")) g.translate(0, -17);
    for (let i = 0; i < 3; i++) {
      const f = 10 + Math.sin(t * (13 + i * 3) + i) * 4;
      g.fillStyle = ["rgba(255,90,20,0.9)", "rgba(255,160,40,0.9)", "rgba(255,230,120,0.95)"][i];
      g.beginPath(); g.moveTo(-8 + i * 2, -29); g.quadraticCurveTo(-3 + i * 3, -29 - f * (1.5 - i * 0.3), 0 + i * 2, -29 - f * (1.9 - i * 0.4)); g.quadraticCurveTo(4 + i, -29 - f, 8 - i * 2, -29); g.fill();
    }
    for (let i = 0; i < 5; i++) {   // smoke: grey puffs drift up and sideways, growing and fading
      const ph = (t * 0.32 + i / 5) % 1, sx = Math.sin(t * 0.9 + i * 2.1) * 6 + ph * 16;
      g.fillStyle = "rgba(150,150,150," + (0.34 * (1 - ph) * Math.min(1, ph * 6)).toFixed(3) + ")";
      g.beginPath(); g.arc(-2 + sx, -40 - ph * 62, 3 + ph * 9, 0, 6.3); g.fill();
    }
    for (let i = 0; i < 4; i++) {   // sparks
      const ph = (t * 0.9 + i / 4) % 1;
      g.fillStyle = "rgba(255,200,80," + (1 - ph).toFixed(2) + ")"; g.fillRect(-4 + Math.sin(t * 3 + i * 2) * 8, -34 - ph * 40, 1.6, 1.6);
    }
  }, liveGlow(g, t, night) {
    const a = (0.35 + 0.1 * Math.sin(t * 15)) * (0.35 + 0.65 * night);
    const gr = g.createRadialGradient(0, -34, 2, 0, -34, 70);
    gr.addColorStop(0, "rgba(255,150,50," + a.toFixed(3) + ")"); gr.addColorStop(1, "rgba(255,90,20,0)");
    g.fillStyle = gr; g.fillRect(-72, -104, 144, 120);
  }};

  /* ---------- Gauteng landmark props ---------- */
  defs.jacaranda = { w: 124, h: 138, glow: false, draw(g, gl, P, r, v) {
    shadow(g, 90);
    g.fillStyle = "rgba(160,110,220,0.5)"; g.beginPath(); g.ellipse(0, -1, 54, 4, 0, 0, 6.28); g.fill();     // fallen blossom
    R(g, "#5a3a26", -4, -60, 8, 60); poly(g, "#5a3a26", [-4, -40, -22, -60, -18, -63, -2, -48]); poly(g, "#5a3a26", [4, -44, 20, -64, 16, -67, 2, -52]);
    const cols = ["#8e5bd0", "#a77be0", "#7a45c2", "#b894ec", "#6f3fb3"];
    for (let i = 0; i < 18; i++) { const a = r() * 6.28, d = r() * 40; circ(g, cols[i % 5], Math.cos(a) * d, -84 + Math.sin(a) * d * 0.5, 13 + r() * 10); }
    for (let i = 0; i < 34; i++) { g.fillStyle = "rgba(238,220,255,0.55)"; g.fillRect((r() - 0.5) * 92, -112 + r() * 54, 3, 2); }
  }};
  defs.glasstower = { w: 80, h: 216, glow: true, draw(g, gl, P, r, v) {
    shadow(g, 70);
    const bw = 46 + (v % 2) * 10, bh = 140 + (v % 3) * 24;
    const grd = g.createLinearGradient(-bw / 2, 0, bw / 2, 0); grd.addColorStop(0, "#8fb8e0"); grd.addColorStop(0.5, "#d6ecff"); grd.addColorStop(1, "#6a9ccc");
    g.fillStyle = grd; g.fillRect(-bw / 2, -bh, bw, bh);
    g.strokeStyle = "rgba(20,50,90,0.3)"; g.lineWidth = 1;
    for (let y = -bh + 8; y < 0; y += 9) { g.beginPath(); g.moveTo(-bw / 2, y); g.lineTo(bw / 2, y); g.stroke(); }
    for (let x = -bw / 2 + 8; x < bw / 2; x += 8) { g.beginPath(); g.moveTo(x, -bh); g.lineTo(x, 0); g.stroke(); }
    for (let y = -bh + 8; y < -6; y += 9) for (let x = -bw / 2 + 2; x < bw / 2 - 5; x += 8) if (r() > 0.55) { gl.fillStyle = "rgba(255,214,120,0.9)"; gl.fillRect(x, y, 5, 6); }
    R(g, "rgba(255,255,255,0.4)", -bw / 2 + 3, -bh, 5, bh);
    R(g, "#46566a", -bw / 2 - 2, -bh - 4, bw + 4, 5);
    if (v % 2) poly(g, "#46566a", [-bw / 2, -bh - 4, 0, -bh - 24, bw / 2, -bh - 4]); else R(g, "#46566a", -1.5, -bh - 28, 3, 24);
    R(g, "#3b4a5c", -bw / 2 - 4, -8, bw + 8, 8);
  }};
  defs.minedump = { w: 252, h: 92, glow: false, draw(g, gl, P, r, v) {
    shadow(g, 230);
    const grd = g.createLinearGradient(0, -78, 0, 0); grd.addColorStop(0, "#f2d77f"); grd.addColorStop(1, "#b98e3c");
    g.fillStyle = grd; g.beginPath(); g.moveTo(-118, 0); g.lineTo(-84, -60); g.lineTo(-70, -74); g.lineTo(70, -74); g.lineTo(88, -58); g.lineTo(120, 0); g.closePath(); g.fill();
    g.strokeStyle = "rgba(120,80,20,0.33)"; g.lineWidth = 1.6;
    for (let i = 0; i < 15; i++) { const x = -86 + i * 12 + r() * 5; g.beginPath(); g.moveTo(x * 0.8, -70); g.lineTo(x * 1.18, -2); g.stroke(); }
    R(g, "rgba(255,255,255,0.28)", -70, -74, 140, 3);
    for (let i = 0; i < 9; i++) { g.fillStyle = "#6f8f3a"; g.beginPath(); g.arc(-110 + r() * 220, -2, 4 + r() * 4, Math.PI, 0); g.fill(); }
  }};
  defs.unionbldg = { w: 272, h: 114, glow: false, draw(g, gl, P, r, v) {
    shadow(g, 250);
    R(g, "#6aa04a", -134, -6, 268, 6);
    for (const sx of [-1, 1]) {                                            // twin towers + copper domes
      R(g, "#d2a56e", sx * 100 - 18, -82, 36, 76); R(g, "#b58a56", sx * 100 - 18, -82, 36, 4);
      g.fillStyle = "#5fa79a"; g.beginPath(); g.arc(sx * 100, -82, 15, Math.PI, 0); g.fill(); R(g, "#5fa79a", sx * 100 - 1, -108, 2, 12);
      for (let j = 0; j < 3; j++) R(g, "#6d4a2a", sx * 100 - 11 + j * 8, -64 + (j % 2) * 18, 5, 12);
    }
    R(g, "#d9b37b", -84, -52, 168, 46); R(g, "#c39a62", -84, -54, 168, 5);
    for (let i = 0; i < 13; i++) R(g, "#efd2a0", -78 + i * 12.6, -48, 5, 40);
    poly(g, "#e2bf8a", [-30, -54, 0, -68, 30, -54]); R(g, "#6d4a2a", -6, -26, 12, 20);
    R(g, "#cfa670", -70, -8, 140, 4);
  }};
  defs.gautrain = { w: 300, h: 150, glow: false, live: true, draw(g, gl, P, r, v) {
    for (const x of [-110, 0, 110]) { R(g, "#b9bdc2", x - 9, -92, 18, 92); R(g, "#9ea3a9", x + 3, -92, 6, 92); }
    R(g, "#c9cdd2", -150, -100, 300, 12); R(g, "#8d9298", -150, -90, 300, 3); R(g, "#e6e9ec", -150, -100, 300, 2.5);
    R(g, "#d8dce0", -150, -118, 300, 2); for (let x = -148; x < 150; x += 20) R(g, "#d8dce0", x, -118, 2, 18);
  }, liveDraw(g, t, P, v) {
    g.save(); g.beginPath(); g.rect(-150, -130, 300, 40); g.clip();
    const tx = ((t * 90) % 560) - 280;
    g.fillStyle = "#f4f6fa"; g.beginPath(); g.roundRect(tx, -118, 150, 20, 8); g.fill();
    g.fillStyle = "#1e56a8"; g.fillRect(tx, -108, 150, 4); g.fillStyle = "#f5c400"; g.fillRect(tx, -104, 150, 2);
    g.fillStyle = "#26323d"; for (let i = 0; i < 9; i++) g.fillRect(tx + 8 + i * 15, -115, 9, 5);
    g.restore();
  }};
  defs.maropeng = { w: 236, h: 86, glow: false, draw(g, gl, P, r, v) {
    shadow(g, 210);
    const grd = g.createLinearGradient(0, -70, 0, 0); grd.addColorStop(0, "#8cb24f"); grd.addColorStop(1, "#5f8a34");
    g.fillStyle = grd; g.beginPath(); g.ellipse(0, 0, 110, 70, 0, Math.PI, 0); g.fill();
    g.fillStyle = "rgba(255,255,255,0.18)"; g.beginPath(); g.ellipse(-26, -44, 38, 14, -0.3, 0, 6.28); g.fill();
    R(g, "#6b6258", -22, -28, 44, 28); g.fillStyle = "#2a2622"; g.beginPath(); g.arc(0, -16, 12, Math.PI, 0); g.fillRect(-12, -16, 24, 16); g.fill();
    R(g, "#8a8176", -26, -30, 52, 4);
    for (let i = 0; i < 7; i++) { g.fillStyle = "#6f8f3a"; g.beginPath(); g.arc(-100 + i * 34 + r() * 10, -2, 5 + r() * 3, Math.PI, 0); g.fill(); }
  }};
  defs.hector = { w: 108, h: 84, glow: false, draw(g, gl, P, r, v) {
    shadow(g, 96);
    R(g, "#8d8579", -50, -12, 100, 12); R(g, "#a29a8d", -50, -14, 100, 3);
    R(g, "#5b5750", -28, -58, 56, 46); R(g, "#6d6962", -28, -58, 56, 4);
    g.fillStyle = "#d8cfbd"; g.beginPath(); g.arc(-2, -44, 5, 0, 6.28); g.fill();                      // the memorial: a boy carried
    R(g, "#d8cfbd", -7, -38, 11, 16); g.strokeStyle = "#d8cfbd"; g.lineWidth = 3; g.beginPath(); g.moveTo(-6, -36); g.lineTo(-14, -26); g.moveTo(3, -36); g.lineTo(12, -30); g.stroke();
    for (let i = 0; i < 7; i++) { circ(g, ["#e63946", "#f7b32b", "#ffffff", "#9b5de5"][i % 4], -40 + i * 13, -15, 2.6); }
    text(g, "1976", 0, -20, 7, "#d8cfbd", "900");
  }};
  defs.bluegum = { w: 86, h: 158, glow: false, draw(g, gl, P, r, v) {
    shadow(g, 56);
    R(g, "#a89a85", -3.4, -120, 6.8, 120); R(g, "rgba(0,0,0,0.12)", 0, -120, 3, 120);
    const cl = ["#6f9a5a", "#5d8a4c", "#82ab68", "#4f7a43"];
    for (let i = 0; i < 12; i++) { const y = -148 + r() * 66, x = (r() - 0.5) * 58; g.fillStyle = cl[i % 4]; g.beginPath(); g.ellipse(x, y, 17 + r() * 9, 6 + r() * 4, (r() - 0.5) * 0.6, 0, 6.28); g.fill(); }
  }};

  defs.highmast = { w: 70, h: 262, glow: false, live: true, draw(g, gl, P, r, v) {
    shadow(g, 30);
    // tapered galvanised pole
    poly(g, "#8b9298", [-3.6, 0, 3.6, 0, 1.6, -236, -1.6, -236]);
    R(g, "rgba(255,255,255,0.25)", -1, -236, 1.2, 236);
    R(g, "#5a6066", -6, -8, 12, 8);
    // lamp ring at the top
    R(g, "#43484d", -20, -240, 40, 4);
    for (let i = -3; i <= 3; i++) { R(g, "#2b2f33", i * 5.4 - 2.4, -246, 4.8, 6); }
    R(g, "#43484d", -2, -252, 4, 12);
  }, liveDraw(g, t, P, v, night) {
    // lamp heads (warm when on)
    for (let i = -3; i <= 3; i++) circ(g, night > 0.3 ? "#fff3c4" : "#c8c8c0", i * 5.4, -243, 2.2);
  }, liveGlow(g, t, night) {
    const flick = 0.95 + 0.05 * Math.sin(t * 31);
    const a = night * flick;
    if (a < 0.02) return;
    const h = haloSprite("255,226,150");
    g.globalAlpha = a * 0.9; g.drawImage(h, -64, -310, 128, 128);
    // downward light cone
    const gr = g.createLinearGradient(0, -240, 0, 6);
    gr.addColorStop(0, "rgba(255,230,160," + (0.26 * a).toFixed(3) + ")"); gr.addColorStop(1, "rgba(255,230,160,0)");
    g.globalAlpha = 1; g.fillStyle = gr;
    g.beginPath(); g.moveTo(-14, -240); g.lineTo(14, -240); g.lineTo(98, 6); g.lineTo(-98, 6); g.closePath(); g.fill();
    // pool of light on the ground
    const pg = g.createRadialGradient(0, 2, 2, 0, 2, 100);
    pg.addColorStop(0, "rgba(255,225,150," + (0.34 * a).toFixed(3) + ")"); pg.addColorStop(1, "rgba(255,225,150,0)");
    g.fillStyle = pg; g.beginPath(); g.ellipse(0, 2, 100, 18, 0, 0, Math.PI * 2); g.fill();
  }};

  function haloSprite(rgb) {
    if (haloCache[rgb]) return haloCache[rgb];
    const c = mk(128, 128), g = c.getContext("2d"); g.scale(S, S);
    const gr = g.createRadialGradient(64, 64, 2, 64, 64, 64);
    gr.addColorStop(0, "rgba(" + rgb + ",0.85)"); gr.addColorStop(0.3, "rgba(" + rgb + ",0.32)"); gr.addColorStop(1, "rgba(" + rgb + ",0)");
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
    return (haloCache[rgb] = c);
  }

  /* ------------------ sprite cache ------------------ */
  function sprite(kind, pal, v) {
    const key = kind + "_" + pal + "_" + (v % 3);
    let s = cache[key];
    if (s) return s;
    const d = defs[kind], P = PALETTES[pal];
    const c = mk(d.w, d.h), g = c.getContext("2d");
    g.scale(S, S); g.translate(d.w / 2, d.h - 4);
    let gc = null, gl = null;
    if (d.glow) { gc = mk(d.w, d.h); gl = gc.getContext("2d"); gl.scale(S, S); gl.translate(d.w / 2, d.h - 4); }
    g.__ppl = [];
    try { d.draw(g, gl, P, rng(v * 31 + pal * 7 + kind.length), v); } catch (e) { /* never let art break the game */ }
    s = cache[key] = { c, gc, ppl: g.__ppl };
    return s;
  }

  /* ------------------ far skyline (Joburg / Soweto / Vaal) ------------------ */
  const FAR_W = 1280, FAR_H = 150;
  const farCache = [];
  /* ---------- Gauteng area landmarks on the far skyline ---------- */
  function FARX(kind, g, gl, sil, r, block, coolingTower, lightsFor) {
    const lite = sil.replace(/,0\.8\)$/, ",0.6)");
    function glassBlock(x, w, h, col) { R(g, col || sil, x, -h, w, h); g.fillStyle = "rgba(255,255,255,0.22)"; g.fillRect(x + 2, -h, 3, h); lightsFor(x, w, h); }
    function dome(x, y, rad, col) { g.fillStyle = col; g.beginPath(); g.arc(x, y, rad, Math.PI, 0); g.fill(); }
    function house(x, y, w, h, col) { R(g, col, x, y - h, w, h); poly(g, "rgba(70,50,40,0.5)", [x - 1, y - h, x + w / 2, y - h - 3, x + w + 1, y - h]); }
    function hillHouses(n, cols, k) {
      for (let i = 0; i < n; i++) {
        const x = r() * FAR_W, y = -(4 + r() * 42) * (0.35 + 0.65 * Math.abs(Math.sin(x / FAR_W * Math.PI * k)));
        house(x, y, 5 + r() * 4, 4 + r() * 3, cols[(r() * cols.length) | 0]);
      }
    }
    switch (kind) {
      case "cbd":
        for (const b of [[40,24,52],[90,18,66],[130,28,48],[170,20,74],[420,22,58],[460,30,72],[500,18,50],[720,24,64],[760,20,80],[800,28,56],[1010,22,68],[1050,26,50],[1150,20,60]]) block(b[0], b[1], b[2]);
        R(g, sil, 300, -118, 34, 118); g.fillStyle = sil; g.beginPath(); g.ellipse(317, -118, 17, 5, 0, 0, 6.28); g.fill();      // Ponte City
        g.fillStyle = "rgba(255,255,255,0.35)"; g.fillRect(312, -112, 10, 36); lightsFor(300, 34, 118);
        R(g, sil, 606, -132, 30, 132); R(g, sil, 612, -146, 18, 14); R(g, sil, 619, -160, 2, 14); lightsFor(606, 30, 132);          // Carlton Centre
        R(g, sil, 880, -16, 260, 4); R(g, sil, 930, -62, 4, 50); R(g, sil, 1040, -62, 4, 50);                                      // Nelson Mandela Bridge
        g.strokeStyle = sil; g.lineWidth = 1; g.beginPath();
        for (let i = 0; i < 7; i++) for (const mx of [932, 1042]) { g.moveTo(mx, -60); g.lineTo(mx - i * 13 - 8, -16); g.moveTo(mx, -60); g.lineTo(mx + i * 13 + 8, -16); }
        g.stroke();
        break;
      case "sandton":
        for (const b of [[30,26,70],[66,22,92],[100,30,60],[250,24,84],[290,28,110],[330,22,76],[560,30,70],[600,26,96],[640,34,64],[820,22,88],[860,28,70],[1010,24,100],[1050,30,66],[1120,20,84]]) glassBlock(b[0], b[1], b[2], lite);
        glassBlock(700, 34, 134, sil); R(g, sil, 712, -150, 10, 16); R(g, sil, 716, -168, 2, 18);
        glassBlock(430, 30, 112, sil); poly(g, sil, [430, -112, 445, -134, 460, -112]);
        break;
      case "rosebank":
        for (let i = 0; i < 22; i++) glassBlock(30 + i * 56 + r() * 20, 22 + r() * 20, 26 + r() * 40, i % 3 ? lite : sil);
        for (let i = 0; i < 16; i++) circ(g, "rgba(70,130,80,0.55)", r() * FAR_W, -8, 10 + r() * 8);
        for (let i = 0; i < 8; i++) circ(g, "rgba(150,90,205,0.5)", r() * FAR_W, -10, 8 + r() * 5);
        break;
      case "alex":
        for (const b of [[200,24,92],[236,20,120],[270,28,80],[300,22,104],[900,26,86],[940,22,112],[980,30,76]]) glassBlock(b[0], b[1], b[2], lite);
        hillHouses(170, ["rgba(230,190,140,0.75)", "rgba(210,130,100,0.75)", "rgba(170,190,210,0.75)", "rgba(240,215,120,0.75)"], 3);
        R(g, sil, 640, -70, 3, 46); R(g, sil, 660, -70, 3, 46); g.fillStyle = sil; g.beginPath(); g.ellipse(651, -78, 14, 10, 0, 0, 6.28); g.fill();
        break;
      case "midrand":
        for (const b of [[40,40,56],[90,34,72],[150,44,50],[420,40,66],[480,36,52],[900,42,60],[960,36,78],[1040,44,54]]) glassBlock(b[0], b[1], b[2], lite);
        R(g, sil, 260, -34, 760, 6); for (let x = 290; x < 1000; x += 90) R(g, sil, x, -34, 8, 34);                                      // Gautrain viaduct
        g.fillStyle = "rgba(250,252,255,0.92)"; g.beginPath(); g.roundRect(560, -48, 130, 14, 5); g.fill(); R(g, "#1e56a8", 560, -40, 130, 3); R(g, "#f5c400", 560, -37, 130, 1.4);
        for (let i = 0; i < 9; i++) R(g, "rgba(40,60,90,0.8)", 570 + i * 13, -46, 8, 4);
        break;
      case "pretoria":
        g.fillStyle = "rgba(150,120,90,0.55)"; g.beginPath(); g.moveTo(180, 0); g.quadraticCurveTo(300, -62, 430, 0); g.fill();       // the Union Buildings hill
        R(g, "rgba(204,164,112,0.95)", 262, -52, 110, 18); for (let i = 0; i < 14; i++) R(g, "rgba(236,208,158,0.95)", 266 + i * 7.6, -50, 2.4, 14);
        R(g, "rgba(204,164,112,0.95)", 252, -60, 20, 26); R(g, "rgba(204,164,112,0.95)", 362, -60, 20, 26); dome(262, -60, 10, "rgba(90,150,140,0.95)"); dome(372, -60, 10, "rgba(90,150,140,0.95)");
        R(g, "rgba(170,140,110,0.85)", 800, -70, 36, 70); dome(818, -70, 14, "rgba(170,140,110,0.85)"); R(g, "rgba(170,140,110,0.85)", 792, -8, 52, 8);   // Voortrekker Monument
        block(560, 24, 58); block(590, 20, 70); block(1000, 22, 60); block(1030, 26, 50);
        for (let i = 0; i < 30; i++) circ(g, "rgba(160,100,210,0.66)", 20 + i * 42 + r() * 18, -6 - r() * 8, 9 + r() * 7);              // jacarandas
        break;
      case "mamelodi":
        hillHouses(180, ["rgba(120,190,160,0.7)", "rgba(230,140,110,0.7)", "rgba(240,210,150,0.7)"], 2.4);
        for (let i = 0; i < 16; i++) circ(g, "rgba(150,90,205,0.55)", r() * FAR_W, -10 - r() * 18, 9 + r() * 6);
        R(g, sil, 300, -90, 2, 90); R(g, sil, 292, -92, 18, 2.4); for (let i = 0; i < 4; i++) { gl.fillStyle = "rgba(255,230,150,0.9)"; gl.fillRect(294 + i * 4.5, FAR_H - 91, 2.4, 2.4); }
        R(g, sil, 860, -64, 3, 38); R(g, sil, 880, -64, 3, 38); g.fillStyle = sil; g.beginPath(); g.ellipse(871, -72, 16, 10, 0, 0, 6.28); g.fill();
        break;
      case "airport":
        for (const b of [[40,50,22],[110,40,30],[600,60,24],[1000,50,26]]) { R(g, lite, b[0], -b[2], b[1], b[2]); g.fillStyle = lite; g.beginPath(); g.ellipse(b[0] + b[1] / 2, -b[2], b[1] / 2, 8, 0, Math.PI, 0); g.fill(); }
        for (let i = 0; i < 22; i++) block(160 + i * 34, 22, 18 + r() * 30);
        R(g, sil, 520, -86, 6, 86); R(g, sil, 508, -104, 30, 18); g.fillStyle = "rgba(120,200,255,0.6)"; g.fillRect(511, -100, 24, 6);
        g.save(); g.translate(900, -116); g.rotate(-0.2); g.fillStyle = "rgba(250,250,255,0.95)"; g.beginPath(); g.ellipse(0, 0, 36, 4.6, 0, 0, 6.28); g.fill();
        poly(g, "rgba(235,238,245,0.97)", [-4, 0, -16, -20, -6, -20, 12, 0]); poly(g, "rgba(235,238,245,0.97)", [-4, 0, -16, 16, -6, 16, 12, 0]); poly(g, "rgba(30,100,170,0.95)", [-32, -2, -38, -14, -30, -14, -24, -2]); g.restore();
        break;
      case "minedump":
        for (const b of [[40,170,54],[330,200,64],[820,180,50],[1060,150,44]]) { g.fillStyle = "rgba(220,182,100,0.8)"; g.beginPath(); g.moveTo(b[0], 0); g.lineTo(b[0] + b[1] * 0.18, -b[2]); g.lineTo(b[0] + b[1] * 0.82, -b[2]); g.lineTo(b[0] + b[1], 0); g.fill(); }
        g.strokeStyle = sil; g.lineWidth = 2.4; g.beginPath(); g.moveTo(640, 0); g.lineTo(656, -96); g.lineTo(672, 0); g.moveTo(646, -48); g.lineTo(666, -48); g.moveTo(650, -72); g.lineTo(662, -72); g.stroke();
        circ(g, sil, 656, -100, 7); R(g, sil, 630, -14, 60, 14);
        for (const x of [560, 590]) { R(g, sil, x, -92, 7, 92); for (let i = 0; i < 3; i++) { g.fillStyle = "rgba(235,235,240," + (0.34 - i * 0.08) + ")"; g.beginPath(); g.arc(x + 3 + i * 6, -98 - i * 10, 6 + i * 4, 0, 6.28); g.fill(); } }
        block(960, 22, 52); block(990, 18, 66);
        break;
      case "cradle":
        g.fillStyle = "rgba(150,130,100,0.62)"; g.beginPath(); g.moveTo(60, 0); g.lineTo(80, -34); g.lineTo(104, -44); g.lineTo(130, -30); g.lineTo(160, 0); g.fill();
        g.beginPath(); g.moveTo(880, 0); g.lineTo(900, -30); g.lineTo(930, -40); g.lineTo(960, -26); g.lineTo(990, 0); g.fill();
        g.fillStyle = "rgba(110,150,80,0.75)"; g.beginPath(); g.ellipse(430, 0, 90, 40, 0, Math.PI, 0); g.fill(); R(g, "rgba(60,50,40,0.7)", 424, -12, 14, 12);   // Maropeng mound
        R(g, sil, 650, -60, 3, 60); g.strokeStyle = sil; g.lineWidth = 2; g.beginPath(); for (let i = 0; i < 4; i++) { const a = i * Math.PI / 2 + 0.4; g.moveTo(651, -60); g.lineTo(651 + Math.cos(a) * 16, -60 + Math.sin(a) * 16); } g.stroke();
        g.beginPath(); g.moveTo(1100, 0); g.lineTo(1110, -62); g.lineTo(1120, 0); g.stroke(); circ(g, sil, 1110, -65, 5);
        for (let i = 0; i < 18; i++) { g.fillStyle = "rgba(120,140,70,0.6)"; g.beginPath(); g.arc(r() * FAR_W, -4, 6 + r() * 5, 0, 6.28); g.fill(); }
        break;
      case "vaal2":
        hillHouses(130, ["rgba(240,190,140,0.7)", "rgba(130,170,210,0.7)", "rgba(235,230,200,0.7)"], 2);
        coolingTower(300, 50, 80); coolingTower(366, 50, 80); R(g, sil, 700, -98, 6, 98); R(g, "rgba(255,70,70,0.9)", 700, -98, 6, 4);
        g.strokeStyle = sil; g.lineWidth = 2.2; g.beginPath(); g.moveTo(900, 0); g.lineTo(914, -84); g.lineTo(928, 0); g.stroke(); circ(g, sil, 914, -88, 6);
        g.fillStyle = "rgba(120,170,210,0.45)"; g.fillRect(0, -5, FAR_W, 5);
        break;
      default: block(100, 26, 70); block(600, 24, 60);
    }
  }

  function farLayer(pal) {
    if (farCache[pal]) return farCache[pal];
    const c = mk(FAR_W, FAR_H), g = c.getContext("2d"); g.scale(S, S);
    const gc = mk(FAR_W, FAR_H), gl = gc.getContext("2d"); gl.scale(S, S);
    const P = PALETTES[pal], r = rng(900 + pal);
    const hz = P.haze;
    g.translate(0, FAR_H);
    // far hills dotted with matchbox houses (periodic so the tile wraps)
    for (let layer = 0; layer < 2; layer++) {
      g.fillStyle = "rgba(" + hz + "," + (0.42 + layer * 0.2) + ")";
      g.beginPath(); g.moveTo(0, 0);
      for (let x = 0; x <= FAR_W; x += 16) {
        const y = -(38 + layer * 14) - Math.sin(x / FAR_W * Math.PI * 2 * (2 + layer)) * (14 + layer * 6) - Math.sin(x / FAR_W * Math.PI * 2 * 5 + layer) * 5;
        g.lineTo(x, y);
      }
      g.lineTo(FAR_W, 0); g.closePath(); g.fill();
      for (let i = 0; i < 70; i++) {
        const x = r() * FAR_W, y = -(38 + layer * 14) - Math.sin(x / FAR_W * Math.PI * 2 * (2 + layer)) * (14 + layer * 6) - Math.sin(x / FAR_W * Math.PI * 2 * 5 + layer) * 5 + 4 + r() * 12;
        g.fillStyle = ["rgba(255,225,190,0.42)", "rgba(210,150,130,0.4)", "rgba(190,205,230,0.4)"][(r() * 3) | 0];
        g.fillRect(x, y, 3 + r() * 2, 2.4);
        if (r() > 0.8) { gl.fillStyle = "rgba(255,210,120,0.9)"; gl.fillRect(x + 1, y - FAR_H + 0.4 + 0, 1.5, 1.5); }
      }
    }
    const sil = "rgba(" + hz + ",0.8)";
    function lightsFor(x, w, h) {   // lit windows into glow canvas (coords: ground at FAR_H)
      for (let yy = FAR_H - h + 5; yy < FAR_H - 4; yy += 7) for (let xx = x + 3; xx < x + w - 2; xx += 5) {
        if (r() > 0.5) { gl.fillStyle = "rgba(255,214,120,0.9)"; gl.fillRect(xx, yy, 2, 2.6); }
      }
    }
    function block(x, w, h) { R(g, sil, x, -h, w, h); lightsFor(x, w, h); }
    function coolingTower(x, w, h) {
      g.fillStyle = sil; g.beginPath(); g.moveTo(x - w / 2, 0);
      g.quadraticCurveTo(x - w * 0.28, -h * 0.5, x - w * 0.36, -h); g.lineTo(x + w * 0.36, -h);
      g.quadraticCurveTo(x + w * 0.28, -h * 0.5, x + w / 2, 0); g.closePath(); g.fill();
      for (let i = 0; i < 4; i++) {   // steam plume
        g.fillStyle = "rgba(235,235,240," + (0.3 - i * 0.06) + ")"; g.beginPath(); g.arc(x + i * 5, -h - 6 - i * 9, 7 + i * 4, 0, Math.PI * 2); g.fill();
      }
    }
    if (P.far === "joburg") {          // Joburg: tall tower with pod, round tower, blocks
      block(40, 22, 58); block(70, 16, 72); block(96, 26, 50); block(260, 20, 64); block(286, 28, 84); block(420, 18, 60);
      block(700, 22, 70); block(730, 18, 56); block(760, 28, 90); block(1000, 20, 66); block(1030, 24, 52); block(1100, 18, 74);
      R(g, sil, 596, -112, 4, 112); circ(g, sil, 598, -90, 9); R(g, sil, 594, -96, 8, 12); R(g, sil, 597, -134, 1.6, 22);
      g.fillStyle = sil; g.fillRect(540, -78, 34, 78); g.beginPath(); g.ellipse(557, -78, 17, 5, 0, 0, Math.PI * 2); g.fill(); lightsFor(540, 34, 78);
    } else if (P.far === "soweto") {   // Soweto: calabash stadium + Orlando towers + blocks
      g.fillStyle = sil; g.beginPath(); g.moveTo(180, 0); g.quadraticCurveTo(190, -46, 250, -52); g.quadraticCurveTo(310, -46, 320, 0); g.closePath(); g.fill();
      for (let i = 0; i < 9; i++) { gl.fillStyle = "rgba(255,200,120," + (0.5 + 0.4 * r()) + ")"; gl.fillRect(200 + i * 11.5, FAR_H - 26 - Math.sin(i / 8 * Math.PI) * 14, 3, 3); }
      coolingTower(620, 48, 76); coolingTower(690, 48, 76);
      R(g, "#d62828", 596, -50, 48, 7); R(g, "#f7b32b", 596, -40, 48, 7); R(g, "#1d6fb8", 666, -50, 48, 7); R(g, "#2a9d4a", 666, -40, 48, 7);
      block(40, 22, 54); block(70, 18, 66); block(420, 24, 70); block(450, 18, 54); block(860, 24, 76); block(1000, 18, 60); block(1030, 24, 80);
    } else if (P.far === "vaal") {                  // Vaal: power-station cooling towers + stacks over the river
      coolingTower(160, 54, 84); coolingTower(230, 54, 84); coolingTower(300, 54, 84);
      R(g, sil, 440, -100, 6, 100); R(g, "rgba(255,70,70,0.9)", 440, -100, 6, 4); R(g, sil, 470, -90, 6, 90);
      block(700, 24, 60); block(730, 20, 76); block(900, 18, 50); block(1100, 28, 68);
      g.fillStyle = "rgba(120,170,210,0.5)"; g.fillRect(0, -6, FAR_W, 6);    // the Vaal river
      for (let i = 0; i < 4; i++) { gl.fillStyle = "rgba(255,70,70,0.9)"; gl.fillRect(441, FAR_H - 100 - 0, 4, 3); }
    } else {
      FARX(P.far, g, gl, sil, r, block, coolingTower, lightsFor);
    }
    return (farCache[pal] = { c, gc });
  }

  /* ------------------ public API ------------------ */
  const WEIGHTS = {
    //            rdp shack spaza tuck shisa rank hawker mural ndeb sheb wash kids fire mast
    kinds:   ["rdp","shack","spaza","tuck","shisa","rank","hawker","mural","ndebele","shebeen","wash","kids","fire","highmast","jacaranda","glasstower","minedump","unionbldg","gautrain","maropeng","hector","bluegum"],
    pal0:    [  3,   3,    2,     1,    2,     1,    2,      1,     1,      1,      2,    1,    1,    1 ],
    pal1:    [  3,   2,    2,     2,    1,     1,    2,      2,     1,      2,      2,    1,    1,    1,  0,0,0,0,0,0, 2, 0 ],
    pal2:    [  2,   3,    2,     1,    2,     2,    1,      2,     2,      1,      2,    1,    1,    1 ]
  };
  function pickKind(pal, lastKind) {
    const ks = WEIGHTS.kinds, Pp = PALETTES[pal];
    const w = Pp.w ? ks.map(k => Pp.w[k] || 0) : ks.map((k, i) => (WEIGHTS["pal" + pal] || [])[i] || 0);
    let tot = 0;
    for (let i = 0; i < ks.length; i++) tot += ks[i] === lastKind ? 0 : w[i];
    let x = Math.random() * tot;
    for (let i = 0; i < ks.length; i++) {
      if (ks[i] === lastKind) continue;
      x -= w[i]; if (x <= 0) return ks[i];
    }
    return ks[0];
  }

  // An idle person: legs stay planted, the upper body breathes and sways about the waist (shopkeepers, hawkers, braai man ...).
  function idlePerson(ctx, e, t) {
    const im = pplImg(e.n); if (!im) return;
    const s = e.hh / im.height, w = im.width * s, h = e.hh;
    const work = e.mode === "work", gest = e.mode === "gesture";
    const amp = work ? 0.05 : gest ? 0.032 : 0.013, fr = work ? 2.6 : gest ? 1.2 : 1.5;
    const sw = Math.sin(t * fr + e.ph), cut = im.height * 0.55;
    ctx.save(); ctx.translate(e.x, 0); if (e.flip) ctx.scale(-1, 1);
    ctx.drawImage(im, 0, cut, im.width, im.height - cut, -w / 2, -h + cut * s, w, (im.height - cut) * s);          // legs: planted
    ctx.translate(0, -h + cut * s + 0.5);
    ctx.rotate(sw * amp);
    ctx.scale(1 + 0.004 * Math.sin(t * 2.2 + e.ph), 1 + 0.014 * Math.sin(t * 2.2 + e.ph));                       // breathing
    ctx.drawImage(im, 0, 0, im.width, cut + 1, -w / 2, -cut * s - 0.5, w, (cut + 1) * s);                         // torso + head
    ctx.restore();
  }

  // Draw one scenery prop (cached sprite + any live animation) on the base line.
  function drawProp(ctx, p, baseY, t, nightAmt) {
    const d = defs[p.kind];
    if (p.x + d.w / 2 < -10 || p.x - d.w / 2 > CW + 10) return;
    const s = sprite(p.kind, p.pal, p.v);
    ctx.drawImage(s.c, p.x - d.w / 2, baseY - d.h + 4, d.w, d.h);
    if (s.ppl && s.ppl.length) {
      ctx.save(); ctx.translate(p.x, baseY);
      for (const e of s.ppl) idlePerson(ctx, e, t + p.t);
      ctx.restore();
    }
    if (d.liveDraw) {
      ctx.save(); ctx.translate(p.x, baseY); ctx.lineCap = "round";
      try { d.liveDraw(ctx, t + p.t, PALETTES[p.pal], p.v, nightAmt); } catch (e) {}
      ctx.restore();
    }
  }
  // Night pass: lit windows, bulbs, fire glow, high-mast light (additive).
  function drawLights(ctx, p, baseY, t, nightAmt) {
    const d = defs[p.kind];
    if (p.x + d.w / 2 + 120 < 0 || p.x - d.w / 2 - 120 > CW) return;
    if (d.glow && nightAmt > 0.02) {
      const s = sprite(p.kind, p.pal, p.v);
      if (s.gc) {
        ctx.globalAlpha = nightAmt * (d.glowPulse ? 0.85 + 0.15 * Math.sin(t * 6 + p.x * 0.05) : 1);
        ctx.drawImage(s.gc, p.x - d.w / 2, baseY - d.h + 4, d.w, d.h);
        ctx.globalAlpha = 1;
      }
    }
    if (d.liveGlow) {
      ctx.save(); ctx.translate(p.x, baseY);
      try { d.liveGlow(ctx, t + p.t, nightAmt); } catch (e) {}
      ctx.restore();
    }
  }
  function drawFar(ctx, pal, scroll, alpha, nightAmt, yTop) {
    const L = farLayer(pal);
    let x = scroll % FAR_W; if (x > 0) x -= FAR_W;
    ctx.save(); ctx.globalAlpha = alpha;
    for (let dx = x; dx < CW; dx += FAR_W) ctx.drawImage(L.c, dx, yTop, FAR_W, FAR_H);
    if (nightAmt > 0.02) {
      ctx.globalCompositeOperation = "lighter"; ctx.globalAlpha = alpha * nightAmt;
      for (let dx = x; dx < CW; dx += FAR_W) ctx.drawImage(L.gc, dx, yTop, FAR_W, FAR_H);
    }
    ctx.restore();
  }

  return { PALETTES, defs, pickKind, drawProp, drawLights, drawFar, haloSprite };
})();

class TownProp {
  constructor(x, kind, pal, v) {
    this.x = x; this.kind = kind; this.pal = pal; this.v = v;
    this.t = rand(0, 20);
    this.w = Town.defs[kind].w;
  }
  update(dt, speed) { this.x -= speed * dt; }
}

// Farm animals wandering the roadside (goats in a little herd, the odd cow).
class AmbientAnimal {
  constructor(x, kind) {
    this.x = x; this.kind = kind; this.t = rand(0, 6);
    this.col = kind === "cow" ? pick(["#e8e2d4", "#6b4a32", "#2a2a2a"]) : pick(["#d8d0c0", "#8a6a4a", "#3a3028"]);
    this.walk = rand(10, 22);
  }
  update(dt, worldSpeed) { this.x -= (worldSpeed * 0.7 - this.walk) * dt; this.t += dt; }
  draw(ctx) {
    ctx.save();
    if (this.kind === "cow") Vec.cow(ctx, this.x, 424, this.t, this.col);
    else Vec.goat(ctx, this.x, 424, this.t, this.col);
    ctx.restore();
  }
}

/* ---------------------------------------------------------
   FX — particles + floating township-slang callouts
--------------------------------------------------------- */
const CELEBRATE_COLORS = ["#ffd23f", "#ff5a3c", "#2a9d4a", "#1d8fe0", "#ffffff", "#ff7bd0"];
class FX {
  constructor() { this.p = []; this.texts = []; this.cap = 150; }
  clear() { this.p.length = 0; this.texts.length = 0; }
  add(x, y, vx, vy, life, size, color, grav, shape) {
    if (this.p.length >= this.cap) this.p.shift();
    this.p.push({ x, y, vx, vy, life, max: life, size, color, grav: grav || 0, shape: shape || "sq", rot: rand(0, 6.28), vr: rand(-8, 8) });
  }
  burst(x, y, n, color, power, grav) {
    for (let i = 0; i < n; i++) {
      const a = rand(0, Math.PI * 2), s = rand(0.35, 1) * (power || 220);
      this.add(x, y, Math.cos(a) * s, Math.sin(a) * s, rand(0.35, 0.7), rand(2, 4.2), color, grav === undefined ? 520 : grav, "sq");
    }
  }
  confetti(x, y, n, power) {
    for (let i = 0; i < n; i++) {
      const a = rand(-Math.PI, 0), s = rand(0.3, 1) * (power || 360);
      this.add(x + rand(-40, 40), y, Math.cos(a) * s, Math.sin(a) * s, rand(0.9, 1.6), rand(3, 6), pick(CELEBRATE_COLORS), 420, "sq");
    }
  }
  dust(x, y, n, dir) {
    for (let i = 0; i < n; i++) this.add(x + rand(-4, 4), y, (dir || -1) * rand(20, 90), rand(-50, -10), rand(0.3, 0.6), rand(3, 7), "rgba(190,170,140,0.5)", -20, "puff");
  }
  text(str, x, y, color, size) {
    if (this.texts.length >= 4) this.texts.shift();
    this.texts.push({ str, x, y, color: color || "#ffd23f", size: size || 30, age: 0, life: 1.05 });
  }
  update(dt, worldSpeed) {
    for (let i = this.p.length - 1; i >= 0; i--) {
      const q = this.p[i];
      q.life -= dt;
      if (q.life <= 0) { this.p.splice(i, 1); continue; }
      q.vy += q.grav * dt; q.x += (q.vx - worldSpeed * 0.2) * dt; q.y += q.vy * dt; q.rot += q.vr * dt;
    }
    for (let i = this.texts.length - 1; i >= 0; i--) {
      const t = this.texts[i];
      t.age += dt; t.y -= 38 * dt;
      if (t.age >= t.life) this.texts.splice(i, 1);
    }
  }
  drawWorld(ctx) {
    for (const q of this.p) {
      const a = clamp(q.life / q.max, 0, 1);
      ctx.globalAlpha = q.shape === "puff" ? a * 0.6 : a;
      ctx.fillStyle = q.color;
      if (q.shape === "puff") { ctx.beginPath(); ctx.arc(q.x, q.y, q.size * (1.6 - a * 0.6), 0, Math.PI * 2); ctx.fill(); }
      else if (q.shape === "line") { ctx.fillRect(q.x, q.y, q.size * 6, 1.4); }
      else { ctx.save(); ctx.translate(q.x, q.y); ctx.rotate(q.rot); ctx.fillRect(-q.size / 2, -q.size / 2, q.size, q.size * 0.7); ctx.restore(); }
    }
    ctx.globalAlpha = 1;
  }
  drawTexts(ctx) {
    ctx.save();
    ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.lineJoin = "round";
    for (const t of this.texts) {
      const k = t.age / t.life;
      const pop = 1 + Math.max(0, 1 - t.age * 7) * 0.6;
      ctx.globalAlpha = k > 0.7 ? 1 - (k - 0.7) / 0.3 : 1;
      ctx.font = "900 " + Math.round(t.size * pop) + "px 'Segoe UI', Arial, sans-serif";
      ctx.lineWidth = 6; ctx.strokeStyle = "rgba(40,10,5,0.95)"; ctx.strokeText(t.str, t.x, t.y);
      ctx.fillStyle = t.color; ctx.fillText(t.str, t.x, t.y);
    }
    ctx.restore();
  }
}

const SLANG_STREAK = ["Sharp!", "Yebo!", "Lekker!", "Go {HERO}!", "Shap shap!", "Ayoba!", "Eish, nice!"];
const SLANG_NEAR = ["Hayibo!", "Ay'bo!", "Hayibo!", "Too close!"];
const MILESTONE_LINES = ["Sharp sharp!", "Yebo yes!", "Lekker, my bru!", "{HERO} is flying!", "Ke nako!", "Ubuntu legend!"];

/* ---------------------------------------------------------
   SOSPANA SONKE SHOP — a township spaza shop that appears every
   ~700 m. Run (or tap ENTER) into the door: GUPTA goes in and
   comes out with +2 lives. Drawn once into an offscreen canvas
   (plus a glow canvas for the sign/windows), then blitted.
--------------------------------------------------------- */
const ShopArt = (function () {
  const W = 262, H = 196;
  const S = Math.min(window.devicePixelRatio || 1, 1.5);
  let sprite = null, glow = null;
  function R(g, c, x, y, w, h) { g.fillStyle = c; g.fillRect(x, y, w, h); }
  function heart(g, x, y, s, col) {
    g.fillStyle = col; g.beginPath();
    g.moveTo(x, y + s * 0.35);
    g.bezierCurveTo(x - s, y - s * 0.5, x - s * 0.6, y - s * 1.0, x, y - s * 0.35);
    g.bezierCurveTo(x + s * 0.6, y - s * 1.0, x + s, y - s * 0.5, x, y + s * 0.35);
    g.fill();
  }
  function halo(gl, cx, cy, r, rgb, a) {
    const gr = gl.createRadialGradient(cx, cy, 1, cx, cy, r);
    gr.addColorStop(0, "rgba(" + rgb + "," + a + ")"); gr.addColorStop(1, "rgba(" + rgb + ",0)");
    gl.fillStyle = gr; gl.fillRect(cx - r, cy - r, r * 2, r * 2);
  }
  function build() {
    const c = document.createElement("canvas"); c.width = Math.ceil(W * S); c.height = Math.ceil(H * S);
    const gc = document.createElement("canvas"); gc.width = c.width; gc.height = c.height;
    const g = c.getContext("2d"), gl = gc.getContext("2d");
    [g, gl].forEach(x => { x.scale(S, S); x.translate(W / 2, H - 4); });
    const OUT = "#2a1810";
    // ground shadow
    g.fillStyle = "rgba(0,0,0,0.25)"; g.beginPath(); g.ellipse(0, 2, 124, 6, 0, 0, Math.PI * 2); g.fill();
    // building
    R(g, "#f7a440", -112, -118, 224, 118);
    R(g, "rgba(255,255,255,0.14)", -112, -118, 224, 6);
    R(g, "rgba(0,0,0,0.12)", -112, -10, 224, 10);
    R(g, "#4a3a2a", -116, -124, 232, 8);              // parapet
    // Ndebele-style painted triangles band under the parapet
    const cols = ["#d62828", "#ffffff", "#1d6fb8", "#2a9d4a", "#111"];
    for (let i = 0; i < 28; i++) { g.fillStyle = cols[i % 5]; g.beginPath(); g.moveTo(-112 + i * 8, -116); g.lineTo(-104 + i * 8, -116); g.lineTo(-108 + i * 8, -108); g.closePath(); g.fill(); }
    // sign board on top
    R(g, "#5a4630", -86, -150, 5, 28); R(g, "#5a4630", 81, -150, 5, 28);
    R(g, "#0f5132", -108, -176, 216, 44);
    g.lineWidth = 3; g.strokeStyle = "#ffd23f"; g.strokeRect(-105, -173, 210, 38);
    g.lineWidth = 2.4; g.strokeStyle = OUT; g.strokeRect(-108, -176, 216, 44);
    g.font = "900 22px 'Segoe UI', Arial, sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
    g.lineWidth = 5; g.strokeStyle = "#07301e"; g.strokeText("SOSPANA SONKE", 0, -153, 194);
    g.fillStyle = "#ffd23f"; g.fillText("SOSPANA SONKE", 0, -153, 194);
    g.fillStyle = "rgba(255,255,255,0.5)"; g.fillText("SOSPANA SONKE", 0, -154.2, 194);
    g.fillStyle = "#ffd23f"; g.fillText("SOSPANA SONKE", 0, -153, 194);
    // sign bulbs + glow
    for (let i = 0; i <= 17; i++) {
      const bx = -102 + i * 12;
      [[bx, -172], [bx, -138]].forEach(([x, y]) => { g.fillStyle = "#fff6c8"; g.beginPath(); g.arc(x, y, 2.2, 0, Math.PI * 2); g.fill(); halo(gl, x, y, 11, "255,230,140", 0.5); });
    }
    halo(gl, 0, -154, 120, "255,224,120", 0.38);
    // awning
    for (let i = 0; i < 16; i++) {
      g.fillStyle = i % 2 ? "#ffffff" : "#d62828";
      g.beginPath(); g.moveTo(-120 + i * 15, -100); g.lineTo(-105 + i * 15, -100); g.lineTo(-107 + i * 15, -84); g.quadraticCurveTo(-112.5 + i * 15, -79, -118 + i * 15, -84); g.closePath(); g.fill();
    }
    g.strokeStyle = OUT; g.lineWidth = 1.6; g.strokeRect(-120, -100, 240, 16);
    // shop windows with shelves of goods
    [-1, 1].forEach(sd => {
      const wx = sd < 0 ? -104 : 54;
      R(g, "#2a1810", wx - 3, -78, 56, 50);
      R(g, "#26363f", wx, -75, 50, 44);
      R(g, "#caa56b", wx, -56, 50, 3); R(g, "#caa56b", wx, -40, 50, 3);
      for (let i = 0; i < 6; i++) { R(g, ["#e63946", "#ffd23f", "#2a9d4a", "#1d6fb8", "#ff7bd0", "#fff"][i], wx + 3 + i * 8, -65, 6, 9); R(g, ["#fff", "#e63946", "#ffd23f", "#2ec4b6", "#ff9f1c", "#1d6fb8"][i], wx + 3 + i * 8, -49, 6, 9); R(g, ["#2a9d4a", "#fff", "#e63946", "#ffd23f", "#1d6fb8", "#ff9f1c"][i], wx + 3 + i * 8, -34, 6, 3.4); }
      g.strokeStyle = "#111"; g.lineWidth = 1.2;
      for (let x = wx; x <= wx + 50; x += 6) { g.beginPath(); g.moveTo(x, -75); g.lineTo(x, -31); g.stroke(); }
      R(g, "rgba(255,255,255,0.12)", wx, -75, 12, 44);
      halo(gl, wx + 25, -53, 44, "255,204,110", 0.5);
    });
    // life hearts painted on the wall + "+2"
    heart(g, -80, -19, 14, "#e63946"); heart(g, -62, -19, 14, "#e63946");
    g.font = "900 11px 'Segoe UI', Arial, sans-serif"; g.fillStyle = "#fff"; g.strokeStyle = OUT; g.lineWidth = 3;
    g.strokeText("+2", -71, -4); g.fillText("+2", -71, -4);
    heart(g, 62, -19, 14, "#e63946"); heart(g, 80, -19, 14, "#e63946");
    g.strokeText("+2", 71, -4); g.fillText("+2", 71, -4);
    // door frame + OPEN sign
    R(g, "#2a1810", -27, -84, 54, 84);
    R(g, "#ffd23f", -25, -82, 50, 6);
    R(g, "#d62828", -16, -97, 32, 11);
    g.font = "900 9px 'Segoe UI', Arial, sans-serif"; g.fillStyle = "#fff"; g.fillText("OPEN", 0, -91.5);
    halo(gl, 0, -91, 30, "255,120,100", 0.4);
    // steps, plants, crates
    R(g, "#9a9486", -34, -4, 68, 4);
    R(g, "#a0522d", -108, -14, 12, 14); g.fillStyle = "#2a8a3a"; g.beginPath(); g.arc(-102, -21, 8, 0, Math.PI * 2); g.fill();
    R(g, "#a0522d", 96, -14, 12, 14); g.fillStyle = "#2a8a3a"; g.beginPath(); g.arc(102, -21, 8, 0, Math.PI * 2); g.fill();
    return { c, gc };
  }
  function ensure() { if (!sprite) { const s = build(); sprite = s.c; glow = s.gc; } }

  // draws the door interior + swinging leaves; open = 0..1
  function door(g, open, t) {
    const dw = 22 * (1 - open * 0.92);
    if (open > 0.02) {
      const gr = g.createRadialGradient(0, -40, 4, 0, -40, 44);
      gr.addColorStop(0, "#fffbe0"); gr.addColorStop(0.5, "#ffd27a"); gr.addColorStop(1, "#c9772e");
      g.fillStyle = gr; g.fillRect(-23, -80, 46, 80);
      // little silhouette shelves inside
      g.fillStyle = "rgba(120,60,20,0.35)"; g.fillRect(-21, -52, 42, 2.5); g.fillRect(-21, -30, 42, 2.5);
    }
    [-1, 1].forEach(sd => {
      g.fillStyle = "#8a5a2b"; g.fillRect(sd < 0 ? -23 : 23 - dw, -80, dw, 80);
      g.strokeStyle = "#2a1810"; g.lineWidth = 1.6; g.strokeRect(sd < 0 ? -23 : 23 - dw, -80, dw, 80);
      if (dw > 8) { g.fillStyle = "#26363f"; g.fillRect((sd < 0 ? -23 : 23 - dw) + 3, -70, dw - 6, 26); g.fillStyle = "#ffd23f"; g.fillRect(sd < 0 ? -23 + dw - 5 : 23 - dw + 3, -36, 2, 6); }
    });
  }

  function draw(ctx, shop, baseY, night, t, showPrompt) {
    ensure();
    const x = shop.x;
    if (x + W / 2 < -10 || x - W / 2 > CW + 10) return;
    ctx.drawImage(sprite, x - W / 2, baseY - H + 4, W, H);
    ctx.save(); ctx.translate(x, baseY); door(ctx, shop.doorOpen, t); ctx.restore();
    if (showPrompt) {
      const b = Math.sin(t * 6) * 5;
      ctx.save(); ctx.translate(x, baseY - H - 16 + b);
      ctx.fillStyle = "#ffd23f"; ctx.strokeStyle = "#2a1810"; ctx.lineWidth = 3; ctx.lineJoin = "round";
      ctx.beginPath(); ctx.moveTo(-14, -14); ctx.lineTo(14, -14); ctx.lineTo(14, -2); ctx.lineTo(24, -2); ctx.lineTo(0, 22); ctx.lineTo(-24, -2); ctx.lineTo(-14, -2); ctx.closePath();
      ctx.stroke(); ctx.fill();
      ctx.font = "900 13px 'Segoe UI', Arial, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "bottom";
      ctx.lineWidth = 4; ctx.strokeStyle = "rgba(20,8,4,0.95)"; ctx.strokeText("RUN IN or press ENTER  +2 LIVES", 0, -18);
      ctx.fillStyle = "#fff"; ctx.fillText("RUN IN or press ENTER  +2 LIVES", 0, -18);
      ctx.restore();
    }
  }
  function drawGlow(ctx, shop, baseY, night, t) {
    ensure();
    const x = shop.x;
    if (x + W / 2 + 60 < 0 || x - W / 2 - 60 > CW) return;
    ctx.globalAlpha = (0.4 + 0.6 * night) * (0.88 + 0.12 * Math.sin(t * 5));
    ctx.drawImage(glow, x - W / 2, baseY - H + 4, W, H);
    ctx.globalAlpha = 1;
    if (shop.doorOpen > 0.1) {
      ctx.save(); ctx.translate(x, baseY - 40);
      const a = shop.doorOpen * (0.5 + 0.2 * Math.sin(t * 20));
      const gr = ctx.createRadialGradient(0, 0, 4, 0, 0, 90);
      gr.addColorStop(0, "rgba(255,230,150," + a.toFixed(3) + ")"); gr.addColorStop(1, "rgba(255,200,100,0)");
      ctx.fillStyle = gr; ctx.fillRect(-90, -90, 180, 180);
      ctx.restore();
    }
  }
  return { draw, drawGlow, W, H };
})();

class Shop {
  constructor(x) { this.x = x; this.used = false; this.doorOpen = 0; this.dead = false; }
  update(dt, speed) { this.x -= speed * dt; if (this.x < -ShopArt.W) this.dead = true; }
}

// Colourful toy pulse shot fired by GUPTA's blaster (hits obstacles only)
const SHOT_COLORS = ["#ff5fa2", "#2ec4b6", "#ffd23f", "#8f6bff", "#ff9f1c"];
class Shot {
  constructor(x, y, vx, vy, color) {
    this.x = x; this.y = y; this.vx = vx; this.vy = vy; this.color = color; this.dead = false;
    this.trail = [];
  }
  get box() { return { x: this.x - 8, y: this.y - 8, w: 16, h: 16 }; }
  update(dt) {
    this.trail.push(this.x, this.y); if (this.trail.length > 12) this.trail.splice(0, 2);
    this.x += this.vx * dt; this.y += this.vy * dt;
    if (this.x > CW + 40 || this.x < -40 || this.y < -40 || this.y > CH + 40) this.dead = true;
  }
  draw(ctx) {
    for (let i = 0; i < this.trail.length; i += 2) {
      const k = i / this.trail.length;
      ctx.globalAlpha = 0.55 * k; ctx.fillStyle = this.color;
      ctx.beginPath(); ctx.arc(this.trail[i], this.trail[i + 1], 2 + 4 * k, 0, Math.PI * 2); ctx.fill();
    }
    ctx.globalAlpha = 1;
    ctx.fillStyle = this.color; ctx.beginPath(); ctx.arc(this.x, this.y, 7.5, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(this.x - 1.6, this.y - 1.6, 3.4, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.85)"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(this.x, this.y, 10, 0, Math.PI * 2); ctx.stroke();
  }
}

/* ---------------------------------------------------------
   MAIN GAME
--------------------------------------------------------- */
const PX_PER_METER = 24;
const TOWN_BASE_Y = 405;                 // base line of the township scenery (just behind the pavement)

class Game {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.dpr = Math.min(window.devicePixelRatio || 1, 2.5);
    computeResponsiveDimensions();
    this._applyCanvasSize();
    window.addEventListener("resize", () => this.handleResize());
    window.addEventListener("orientationchange", () => setTimeout(() => this.handleResize(), 60));

    this.state = "LOADING";
    this.player = new Player();
    this.weather = new Weather();
    this.dayNight = new DayNight();

    this.obstacles = [];
    this.hazards = [];
    this.collectibles = [];
    this.powerups = [];
    this.bgProps = [];
    this.poles = [];
    this.ambientPeds = [];
    this.ambientTaxis = [];
    this.townProps = [];
    this.animals = [];
    this.fx = new FX();
    this.time = 0;

    this.combo = 0;
    this.comboTimer = 0;
    this.bestCombo = 0;
    this.nearMisses = 0;
    this.comboFlash = 0;
    this.rideTimer = 0;
    this.rideBoost = 1;
    this.animalTimer = rand(20, 35);
    this.dustTimer = 0;
    this.lastBgKey = AREAS[0].key;
    this.signs = []; this.streetKey = "";
    this.bgPrevKey = null;
    this.bgFade = 1;
    this.stageFx = null;
    this.banner = null;
    this.bannerQueue = [];
    this.flash = 0;
    this.shakeDur = 0.3;

    this.ammo = 0;
    this.shots = [];
    this.fireCd = 0;
    this.shop = null;
    this.nextShopAt = 300;
    this.shopScene = null;
    this.shopVisits = 0;
    this.rescueOffered = false;
    this._creditsTimer = null;

    this.bgScrollA = 0;
    this.bgScrollB = 0;

    this.spawnTimer = 1.2;
    this.powerupTimer = rand(14, 20);
    this.bgPropTimer = 0;
    this.poleTimer = 0;
    this.pedTimer = rand(2, 5);
    this.taxiTimer = rand(5, 10);
    this._propSeed = 1;

    this.distance = 0;
    this.cash = 0;
    this.score = 0;
    this.speed = 230;
    this.magnetTimer = 0;
    this.multiTimer = 0;
    this.bootsTimer = 0;

    this.zoneIndex = -1;
    this.milestoneNext = 500;
    this.shakeTime = 0;
    this.shakeMag = 0;

    this.best = readBest(DIFF_KEY);
    this.runDiff = DIFF_KEY;

    this._initBgRow(true);
    this._initTownRow();
  }

  /* ---------------- township scenery row ---------------- */
  townPalFor(key) { return (AREA_BY_KEY[key] || AREAS[0]).pal; }

  _spawnTownProp(edgeX) {
    const pal = this.townPalFor(this.currentBgKey());
    const last = this.townProps[this.townProps.length - 1];
    const kind = Town.pickKind(pal, last ? last.kind : null);
    const w = Town.defs[kind].w;
    const gap = kind === "highmast" ? rand(30, 120) : rand(20, 110);
    const p = new TownProp(edgeX + gap + w / 2, kind, pal, randInt(0, 2));
    this.townProps.push(p);
    return p.x + w / 2;
  }

  _fillTownRow() {
    const last = this.townProps[this.townProps.length - 1];
    let right = last ? last.x + last.w / 2 : -120;
    let guard = 0;
    while (right < CW + 260 && guard++ < 40) right = this._spawnTownProp(right);
  }
  _initTownRow() { this._fillTownRow(); }

  /* ---------------- responsive canvas ---------------- */
  _applyCanvasSize() {
    this.dpr = Math.min(window.devicePixelRatio || 1, 2.5);
    this.canvas.width = Math.round(CW * this.dpr);
    this.canvas.height = Math.round(CH * this.dpr);
    this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
  }

  handleResize() {
    const oldCW = CW;
    computeResponsiveDimensions();
    this._applyCanvasSize();
    // Rebuild the background-prop row so it fills newly-revealed width
    // (e.g. rotating a phone or resizing a browser window wider).
    if (CW > oldCW) { this._initBgRow(false); this._fillTownRow(); }
  }

  difficultyTier() {
    const d = this.distance, T = DIFF().tiers;
    if (d < T[0]) return 0;
    if (d < T[1]) return 1;
    if (d < T[2]) return 2;
    return 3;
  }

  currentBgKey() { return areaAt(this.distance).key; }

  // After a full pass through all 3 painted scenes, re-grade them with a
  // different color mood so a long run keeps feeling fresh without needing
  // new art — cool dawn, deep dusk, dusty overcast, then back to the
  // original golden-hour look.
  bgMood() {
    // lap 1 = the plates exactly as painted; every later lap gets a different soft colour grade so a repeat never looks the same
    const lap = Journey.slotAt(this.distance).lap;
    return lap === 0 ? null : BG_TINTS[(lap - 1) % BG_TINTS.length];
  }

  // Easy ramp: 230 px/s at the start, rising slowly to a cap of 460 (was 260 -> 720).
  targetSpeed() {
    const d = this.distance, S = DIFF().speed;
    return S.start + clamp(d * S.gain, 0, S.ramp) + Math.min(S.late, Math.max(0, d - 1400) * 0.02);
  }

  _initBgRow(instant) {
    let x = instant ? -40 : CW + 60;
    while (x < CW + 400) {
      this.bgProps.push(new BackgroundProp(x, this._propSeed++));
      x += rand(150, 230);
    }
  }

  /* ---------------- spawning ---------------- */
  _coinArc(x0, n, baseY, arcH, step) {
    for (let i = 0; i < n; i++) {
      const k = n === 1 ? 0.5 : i / (n - 1);
      this.collectibles.push(new Collectible(x0 + i * (step || 44), baseY - Math.sin(k * Math.PI) * arcH, "coin"));
    }
  }

  spawnPattern() {
    const tier = this.difficultyTier();
    const roll = Math.random();

    // Tall stack (tier>=2, rare): needs a double / triple jump.
    if (tier >= 2 && roll < 0.05) {
      const ts = new TallStack();
      this.obstacles.push(ts);
      this._coinArc(ts.x - 40, 5, GROUND_Y - 150, 40, 20);
      if (!this._seenTallStack) {
        this._seenTallStack = true;
        UI.flashZoneBanner("⬆️⬆️ Too tall for one jump — chain your jumps!");
      }
      return;
    }

    // Roadworks cluster (tier>=2): just two static obstacles, well spaced, with coins over them
    if (tier >= 2 && roll < 0.12) {
      let x = CW + 60;
      for (let i = 0; i < 2; i++) {
        const o = new Obstacle(pick(OBSTACLE_TYPES));
        o.x = x;
        this.obstacles.push(o);
        x += rand(210, 260);
      }
      this._coinArc(CW + 60, 7, GROUND_Y - 120, 44, 40);
      return;
    }

    // Moving hazard: a rolling tyre (dogs only if ROAD_DOGS). No people, no cats.
    if (tier >= 1 && roll < 0.20) {
      const useDog = ROAD_DOGS && Math.random() < 0.5;
      this.hazards.push(new MovingHazard(useDog ? "dog" : "tyre"));
      if (useDog && Math.random() < 0.5) Audio_.bark();
      return;
    }

    // Collectible burst — generous coin arcs, sometimes a big-value item
    if (roll < (tier === 0 ? DIFF().collect[0] : DIFF().collect[1])) {
      const specialRoll = Math.random();
      if (specialRoll < 0.10) {
        this.collectibles.push(new Collectible(CW + 80, GROUND_Y - 80, "moneybag"));
        this._coinArc(CW + 140, 4, GROUND_Y - 70, 30, 40);
      } else if (specialRoll < 0.22) {
        this.collectibles.push(new Collectible(CW + 80, GROUND_Y - 80, "gem"));
        this._coinArc(CW + 140, 4, GROUND_Y - 70, 30, 40);
      } else if (specialRoll < 0.30 && this.player.lives < DIFF().lives && Math.random() < DIFF().heartKeep) {
        this.collectibles.push(new Collectible(CW + 80, GROUND_Y - 80, "heart"));
      } else if (specialRoll < 0.38) {
        this.collectibles.push(new Collectible(CW + 80, GROUND_Y - 90, "star"));
        this._coinArc(CW + 130, 5, GROUND_Y - 70, 40, 44);
      } else {
        this._coinArc(CW + 60, randInt(6, 9), GROUND_Y - 74, 70, 44);
      }
      return;
    }

    // Default: a single static obstacle with a coin arc over it as a reward for jumping
    const o = new Obstacle(pick(OBSTACLE_TYPES));
    this.obstacles.push(o);
    if (Math.random() < 0.7) this._coinArc(o.x - 50, 4, GROUND_Y - 110, 45, 34);
    // harder levels: a second obstacle follows (always far enough behind to be jumpable: >= 0.62 s of running)
    if (Math.random() < DIFF().doubleChance) {
      const o2 = new Obstacle(pick(OBSTACLE_TYPES));
      o2.x = o.x + Math.max(230, this.speed * 0.62) + rand(0, 50);
      this.obstacles.push(o2);
    }
  }

  maybeSpawnPowerup() {
    let kind = pick(["shield", "shield", "magnet", "magnet", "multi", "boots", "board", "board", "gun", "gun"]);
    // The Quantum Taxi is the rare, special one - only after the first ~250m
    if (this.distance > 250 && Math.random() < 0.18) kind = "taxi";
    if (kind === "gun" && this.ammo > 12) kind = "shield";
    this.powerups.push(new PowerUp(CW + 80, GROUND_Y - 72, kind));
  }

  /* ---------------- lifecycle ---------------- */
  _debugArea(i) {      // jump straight to an area (tests / screenshots)
    this.distance = areaStart(i) + 3;
    this.dayNight.t = DAY_CYCLE_LENGTH * 0.5;
  }

  startRun() {
    this.player = new Player();
    this.obstacles = [];
    this.hazards = [];
    this.collectibles = [];
    this.powerups = [];
    this.ambientPeds = [];
    this.ambientTaxis = [];
    this.townProps = [];
    this.animals = [];
    this.fx.clear();
    this.combo = 0; this.comboTimer = 0; this.bestCombo = 0; this.nearMisses = 0;
    this.rideTimer = 0; this.rideBoost = 1;
    this.ammo = 0; this.shots = []; this.fireCd = 0;
    this.shop = null; this.nextShopAt = DIFF().shopFirst; this.shopScene = null; this.shopVisits = 0; this.rescueOffered = false;
    clearTimeout(this._creditsTimer);
    this.dayNight.t = DAY_CYCLE_LENGTH * 0.5 + rand(-4, 4);   // every run starts in bright daylight
    this.stageFx = null; this.banner = null; this.bannerQueue = []; this.flash = 0;
    this.bgPrevKey = null; this.bgFade = 1; this.lastBgKey = Journey.slot(0).area.key;
    this.signs = []; this.streetKey = "";
    this.distance = 0;
    this.cash = 0;
    this.score = 0;
    this.runDiff = DIFF_KEY; this.best = readBest(DIFF_KEY);
    this.speed = DIFF().speed.start;
    this.spawnTimer = 1.4;
    this.powerupTimer = rand(14, 20) * DIFF().powerupMul;
    this.magnetTimer = 0;
    this.multiTimer = 0;
    this.bootsTimer = 0;
    this.zoneIndex = -1;
    this.milestoneNext = 500;
    this.weather = new Weather();
    this._fillTownRow();
    this.state = "PLAYING";
    UI.showHUD(true);
    UI.hideAllScreens();
    PlateStore.ensure(Journey.slot(0).area.key); PlateStore.ensure(Journey.slot(1).area.key); PlateStore.keep([Journey.slot(0).area.key, Journey.slot(1).area.key]);
    UI.setHero(heroName()); UI.setDiff();
    this._triggerZoneBanner();
  }

  _triggerZoneBanner() {
    const sl = Journey.slotAt(this.distance), ai = sl.n, a = sl.area, si = streetIndexAt(this.distance);
    const key = ai + ":" + si;
    if (key === this.streetKey) return;
    const first = this.streetKey === "";
    this.streetKey = key;
    const street = a.streets[si];
    UI.setZone(street + " · " + a.name);
    UI.setJourney(sl.pos + 1, AREAS.length, sl.lap + 1, a.name, a.regionIdx);
    if (!first) { UI.flashZoneBanner("📍 " + street + " — " + a.name); Audio_.zone(); }
    this.signs.push(new AreaSign(first ? CW * 0.66 : CW + 140, street, a));
  }

  gameOver() {
    this.state = "GAMEOVER";
    Audio_.gameOver();
    const distM = Math.floor(this.distance);
    const isNewBest = distM > this.best.dist;
    if (isNewBest) this.best.dist = distM;
    if (this.cash > this.best.cash) this.best.cash = this.cash;
    writeBest(this.runDiff, this.best);
    if (distM >= WIN_DISTANCE) {
      clearTimeout(this._creditsTimer);
      this._creditsTimer = setTimeout(() => { if (this.state === "GAMEOVER" && window.__bvhOpenCredits) window.__bvhOpenCredits("gameover"); }, 2800);
    }
    UI.showGameOver({ level: this.runDiff, dist: distM, cash: this.cash, score: Math.floor(this.score * DIFFICULTY[this.runDiff].scoreMul), bestDist: this.best.dist, bestCash: this.best.cash, isNewBest, combo: this.bestCombo, near: this.nearMisses });
    UI.showHUD(false);
  }

  triggerShake(mag, time) {
    // never let a small shake cancel a bigger one that is still running
    if (this.shakeTime > 0 && this.shakeMag * (this.shakeTime / this.shakeDur) > mag) return;
    this.shakeMag = mag; this.shakeTime = time; this.shakeDur = time;
  }

  /* ---------------- combo / callouts / banners ---------------- */
  comboMult() { return clamp(1 + Math.floor(this.combo / 8), 1, 5); }

  _calloutPos() { return { x: PLAYER_X + 44, y: Math.max(96, this.player.y - PLAYER_H - 26) }; }

  _addCombo(n) {
    const beforeMult = this.comboMult(), beforeTier = Math.floor(this.combo / 5);
    this.combo += n;
    this.comboTimer = 3.4;
    this.comboFlash = 1;
    if (this.combo > this.bestCombo) this.bestCombo = this.combo;
    const afterMult = this.comboMult(), tier = Math.floor(this.combo / 5);
    const pos = this._calloutPos();
    if (afterMult > beforeMult) {
      this.fx.text("x" + afterMult + " " + fmtHero(SLANG_STREAK[(afterMult - 1) % SLANG_STREAK.length]), pos.x, pos.y, "#7cff6b", 34);
      Audio_.combo(afterMult);
      this.triggerShake(3, 0.15);
    } else if (tier > beforeTier) {
      this.fx.text(fmtHero(SLANG_STREAK[(tier - 1) % SLANG_STREAK.length]), pos.x, pos.y, "#ffd23f", 30);
      Audio_.combo(Math.min(tier, 5));
    }
  }

  _dropCombo(hurt) {
    if (this.combo >= 5 && !hurt) {
      const pos = this._calloutPos();
      this.fx.text("Streak over", pos.x, pos.y, "#cfd8dc", 22);
    }
    this.combo = 0; this.comboTimer = 0;
  }

  _pushBanner(b) {
    b.t = 0;
    if (!this.banner) this.banner = b;
    else if (this.bannerQueue.length < 3) this.bannerQueue.push(b);
  }

  _hitPlayer() {
    const p = this.player;
    const hadShield = p.shield, wasInv = p.invuln > 0;
    const lost = p.hit();
    const px = PLAYER_X + 10, py = p.y - PLAYER_H * 0.5;
    if (lost) {
      this.triggerShake(8, 0.3);
      this.fx.burst(px, py, 16, "#ff5a3c", 260);
      this.fx.burst(px, py, 8, "#ffd23f", 200);
      this._dropCombo(true);
      this.fx.text("Ay'bo!", px + 30, Math.max(96, py - 70), "#ff6b5a", 34);
    } else if (hadShield && !wasInv && !p.shield) {
      this.triggerShake(3, 0.15);
      this.fx.burst(px, py, 14, "#5ad1ff", 240, 100);
      this.fx.text("Shield!", px + 30, Math.max(96, py - 70), "#5ad1ff", 28);
    }
  }

  _smash(o) {
    o.dead = true;
    const ox = o.x, oy = GROUND_Y - 24;
    this.fx.burst(ox, oy, 12, "#ffd23f", 300);
    this.fx.burst(ox, oy, 8, "#ff8a1f", 240);
    this.fx.dust(ox, GROUND_Y - 2, 5, 1);
    this.score += 30 * this.comboMult();
    this._addCombo(1);
    this.triggerShake(4, 0.15);
    Audio_.smash();
    if (Math.random() < 0.3) { const pos = this._calloutPos(); this.fx.text(pick(["Lekker!", "Sharp!", "Yebo!"]), pos.x + 50, pos.y, "#ffd23f", 28); }
  }

  _startTaxiRide() {
    this.rideTimer = 6;
    this.player.ride = true;
    this.player.rideKind = "taxi";
    this.fx.burst(PLAYER_X + 10, this.player.y - 40, 22, "#ffd23f", 340);
    this.fx.burst(PLAYER_X + 10, this.player.y - 40, 12, "#5ad1ff", 280);
    this._pushBanner({ text: "QUANTUM TAXI!", sub: "Smash through everything - Hayibo!", dur: 2.0, kind: "taxi" });
    this.triggerShake(5, 0.35);
    Audio_.taxiRide();
  }

  _endTaxiRide() {
    this.rideTimer = 0;
    this.player.ride = false;
    this.player.rideKind = "";
    this.player.invuln = Math.max(this.player.invuln, 0.9);   // short grace period as you hop off
    const pos = this._calloutPos();
    this.fx.text("Hop off!", pos.x, pos.y, "#ffd23f", 26);
  }

  _startStageTransition(newKey) {
    this.bgPrevKey = this.lastBgKey;
    this.lastBgKey = newKey;
    this.bgFade = 0;
    PlateStore.ensure(newKey);
    const pal = this.townPalFor(newKey);
    this.stageFx = { t: 0, dur: 1.7, pal };
    this.flash = 1;
    this.triggerShake(6, 0.5);
    this.fx.confetti(CW / 2, 200, 26, 380);
    Audio_.stage();
    const area = AREA_BY_KEY[newKey] || AREAS[0], sl = Journey.slotAt(this.distance);
    this._pushBanner({ text: "Now entering: " + area.name, sub: REGIONS[area.regionIdx] + " · " + area.streets.slice(0, 2).join(" · "), dur: 2.9, kind: "stage" });
    const nxt = Journey.slot(sl.n + 1).area;
    PlateStore.ensure(nxt.key); PlateStore.keep([newKey, this.bgPrevKey, nxt.key]);
  }

  /* ---------------- skateboard ---------------- */
  _startBoard() {
    this.rideTimer = 8;
    this.player.ride = true;
    this.player.rideKind = "board";
    this.fx.burst(PLAYER_X + 10, this.player.y - 10, 18, "#2ec4b6", 300);
    this.fx.burst(PLAYER_X + 10, this.player.y - 10, 10, "#ff9f1c", 240);
    this._pushBanner({ text: "SKATEBOARD!", sub: heroName() + " is rolling - unstoppable!", dur: 2.0, kind: "board" });
    this.triggerShake(3, 0.2);
    Audio_.board();
  }

  /* ---------------- toy pulse blaster ---------------- */
  _giveAmmo() {
    this.ammo = Math.min(30, this.ammo + 14);
    this.fx.burst(PLAYER_X + 40, this.player.y - 60, 14, "#ff5fa2", 260);
    UI.flashZoneBanner("💥 BLASTER! Auto-fires at obstacles - or tap FIRE / press F");
  }

  _targets() {
    const out = [];
    for (const o of this.obstacles) if (!o.dead) out.push(o);
    for (const h of this.hazards) if (!h.dead && h.type === "tyre") out.push(h);   // never animals, never people
    return out;
  }

  _nearestTarget(minDx, maxDx) {
    let best = null, bd = 1e9;
    const px = PLAYER_X + 40;
    for (const t of this._targets()) {
      const dx = t.x - px;
      if (dx > minDx && dx < maxDx && dx < bd) { bd = dx; best = t; }
    }
    return best;
  }

  _fire() {
    if (this.state !== "PLAYING" || this.ammo <= 0 || this.fireCd > 0 || this.shopScene) return false;
    this.ammo--;
    this.fireCd = 0.2;
    const p = this.player;
    p.shootTimer = 0.22;
    const mz = p.muzzle(), ox = mz.x, oy = mz.y;
    const tgt = this._nearestTarget(30, CW);
    const sp = 980;
    let vx = sp, vy = 0;
    if (tgt) {
      const hb = tgt.hitbox, dx = Math.max(10, hb.x + hb.w / 2 - ox), tt = dx / sp;
      const ty = hb.y + hb.h / 2, tx = hb.x + hb.w / 2 - (this.speed * this.rideBoost) * tt * (tgt.type === "tyre" ? 1.1 : 1);
      const ddx = tx - ox, ddy = ty - oy, d = Math.hypot(ddx, ddy) || 1;
      vx = ddx / d * sp; vy = ddy / d * sp;
    }
    this.shots.push(new Shot(ox, oy, vx, vy, SHOT_COLORS[(this._shotIdx = (this._shotIdx || 0) + 1) % SHOT_COLORS.length]));
    this.fx.burst(ox + 4, oy, 5, "#ffe14d", 140, 0);
    Audio_.zap();
    return true;
  }

  _updateShots(dt) {
    for (const s of this.shots) {
      s.update(dt);
      if (s.dead) continue;
      const sb = s.box;
      for (const t of this._targets()) {
        if (t.dead) continue;
        const hb = t.hitbox;
        if (aabbOverlap(sb, { x: hb.x - 8, y: hb.y - 8, w: hb.w + 16, h: hb.h + 16 })) {
          s.dead = true;
          t.hp = (t.hp || 1) - 1;
          this.fx.burst(s.x, s.y, 8, s.color, 220);
          if (t.hp <= 0) {
            t.dead = true;
            const cx = hb.x + hb.w / 2, cy = hb.y + hb.h / 2;
            this.fx.burst(cx, cy, 14, "#ffd23f", 300);
            this.fx.burst(cx, cy, 8, "#ff5fa2", 240);
            this.fx.dust(cx, GROUND_Y - 2, 4, 1);
            this.score += 25 * this.comboMult();
            this._addCombo(1);
            this.triggerShake(2, 0.1);
            Audio_.smash();
            if (Math.random() < 0.4) this.fx.text(pick(["Pow!", "Boom!", "Zap!"]), cx, cy - 36, "#ff8ad0", 26);
          } else Audio_.coin();
          break;
        }
      }
    }
    this.shots = this.shots.filter(s => !s.dead);
  }

  /* ---------------- Sospana Sonke shop ---------------- */
  _shopNear() {
    const s = this.shop;
    return !!(s && !s.used && !this.shopScene && Math.abs(s.x - (PLAYER_X + 10)) < 260 && s.x > PLAYER_X - 60);
  }

  _spawnShop() {
    this.shop = new Shop(CW + 340);
    // clear anything that would be near the door; coins lead the way in
    this.obstacles = this.obstacles.filter(o => o.x < PLAYER_X + 300);
    this.hazards = this.hazards.filter(h => h.x < PLAYER_X + 300);
    this.powerups = this.powerups.filter(p => p.x < PLAYER_X + 300);
    for (let i = 0; i < 6; i++) this.collectibles.push(new Collectible(this.shop.x - 330 + i * 50, GROUND_Y - 34, "coin"));
    this.nextShopAt = this.distance + DIFF().shopEvery;
    UI.flashZoneBanner("🏪 SOSPANA SONKE ahead - run in for +2 lives!");
  }

  tryEnterShop() {
    const s = this.shop;
    if (!s || s.used || this.shopScene || this.state !== "PLAYING") return false;
    if (Math.abs(s.x - (PLAYER_X + 10)) > 270) return false;
    this._enterShop();
    return true;
  }

  _enterShop() {
    this.shopScene = { t: 0, gave: false, fromX: this.shop.x };
    this.player.shopLock = true;
    this.player.vy = 0;
    this.triggerShake(2, 0.12);
  }

  _shopWorldMul() {
    const s = this.shopScene;
    if (!s) return 1;
    const t = s.t;
    if (t < 0.3) return lerp(1, 0.04, t / 0.3);
    if (t < 1.7) return 0.04;
    if (t < 2.1) return lerp(0.04, 1, (t - 1.7) / 0.4);
    return 1;
  }

  _updateShop(dt, spd) {
    if (!this.shop && this.distance >= this.nextShopAt) this._spawnShop();
    const shop = this.shop;
    if (!shop) return;
    shop.update(dt, spd);
    const hx = PLAYER_X + 10;
    const sc = this.shopScene;
    if (!sc) {
      shop.doorOpen = Math.max(0, shop.doorOpen - dt * 3);
      // walking / running into the door
      if (!shop.used && Math.abs(shop.x - hx) < 36 && this.player.y > GROUND_Y - 90) this._enterShop();
    } else {
      sc.t += dt;
      const t = sc.t;
      // snap the door under GUPTA
      if (t < 0.9) shop.x += (hx - shop.x) * clamp(dt * 9, 0, 1);
      shop.doorOpen = t < 0.3 ? t / 0.3 : (t < 1.7 ? 1 : Math.max(0, 1 - (t - 1.7) / 0.3));
      this.player.entryK = t < 0.5 ? t / 0.5 : (t < 1.3 ? 1 : Math.max(0, 1 - (t - 1.3) / 0.5));
      if (t >= 0.9 && !sc.gave) {
        sc.gave = true;
        const before = this.player.lives;
        this.player.lives = Math.min(MAX_LIVES, this.player.lives + 2);
        this.shopVisits++;
        this.score += 100;
        this._pushBanner({ text: "+2 LIVES - Sospana Sonke!", sub: "Respect, " + heroName() + "! (" + before + " → " + this.player.lives + " lives)", dur: 2.6, kind: "shop" });
        this.fx.confetti(CW / 2, 160, 44, 440);
        this.fx.confetti(shop.x, GROUND_Y - 120, 30, 300);
        for (let i = 0; i < 12; i++) this.fx.add(shop.x + rand(-30, 30), GROUND_Y - 80, rand(-120, 120), rand(-320, -120), rand(0.8, 1.4), rand(5, 8), "#ff3d5a", 260, "sq");
        this.fx.text("+2 ❤", PLAYER_X + 40, GROUND_Y - 130, "#ff6b8a", 36);
        this.triggerShake(4, 0.25);
        Audio_.shop();
      }
      if (t >= 2.1) {
        this.shopScene = null;
        shop.used = true;
        this.player.shopLock = false;
        this.player.entryK = 0;
        this.player.invuln = Math.max(this.player.invuln, 1.2);
        shop.doorOpen = 0;
      }
    }
    if (shop.dead) this.shop = null;
  }

  _updateExtras(dt, spd) {
    this.player.hasGun = this.ammo > 0;
    if (this.fireCd > 0) this.fireCd -= dt;
    this._updateShop(dt, spd);
    this._updateShots(dt);

    // auto-fire the blaster at the nearest obstacle in range
    if (AUTO_FIRE && this.ammo > 0 && this.fireCd <= 0 && !this.shopScene) {
      const t = this._nearestTarget(60, 400);
      if (t) this._fire();
    }

    // skateboard: sparks and rolling
    if (this.rideTimer > 0 && this.player.rideKind === "board" && this.player.grounded) {
      this._sparkT = (this._sparkT || 0) - dt;
      if (this._sparkT <= 0) {
        this._sparkT = 0.045;
        this.fx.add(PLAYER_X + 10 + pick([-17, 17]), GROUND_Y - 2, -rand(80, 240), -rand(40, 140), rand(0.25, 0.5), rand(1.6, 3), pick(["#ffd23f", "#ff8a1f", "#ffffff"]), 520, "sq");
      }
    }

    // rescue: one life left -> a skateboard appears
    const p = this.player;
    if (p.lives > 1) this.rescueOffered = false;
    else if (DIFF().rescue && p.lives === 1 && !this.rescueOffered && this.rideTimer <= 0 && !this.shopScene && this.distance > 40) {
      this.rescueOffered = true;
      this.obstacles = this.obstacles.filter(o => o.x < PLAYER_X + 200);
      this.hazards = this.hazards.filter(h => h.x < PLAYER_X + 200);
      this.powerups = this.powerups.filter(q => q.kind !== "board");
      this.powerups.push(new PowerUp(CW + 40, GROUND_Y - 62, "board"));
      this.fx.text(heroName() + " to the rescue!", PLAYER_X + 90, 120, "#2ec4b6", 28);
    }
  }

  _drawJumpPips(ctx) {
    if (this.state !== "PLAYING" || this.player.entryK > 0) return;
    const p = this.player, total = p.maxJumps, left = p.jumpsLeft;
    const cx = PLAYER_X + 9, y = GROUND_Y + 24, gap = 15;
    ctx.save();
    for (let i = 0; i < total; i++) {
      const x = cx + (i - (total - 1) / 2) * gap;
      ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI * 2);
      if (i < left) { ctx.fillStyle = "#ffd23f"; ctx.fill(); ctx.lineWidth = 1.6; ctx.strokeStyle = "#7a3f00"; ctx.stroke(); }
      else { ctx.fillStyle = "rgba(0,0,0,0.25)"; ctx.fill(); ctx.lineWidth = 1.4; ctx.strokeStyle = "rgba(255,255,255,0.45)"; ctx.stroke(); }
    }
    ctx.restore();
  }

  _updateNearMiss(pbox) {
    if (this.rideTimer > 0) return;
    const scan = (o) => {
      if (o.dead || o._nm) return;
      const hb = o.hitbox;
      const horiz = hb.x < pbox.x + pbox.w + 22 && hb.x + hb.w > pbox.x - 22;
      if (horiz) {
        const gap = hb.y - (pbox.y + pbox.h);
        if (o._minGap === undefined || gap < o._minGap) o._minGap = gap;
      } else if (o._minGap !== undefined && hb.x + hb.w <= pbox.x - 22) {
        o._nm = true;
        if (o._minGap >= 0 && o._minGap <= DIFF().nearMiss && this.player.invuln <= 0) this._nearMiss(hb);
      }
    };
    for (const o of this.obstacles) scan(o);
    for (const h of this.hazards) scan(h);
  }

  _nearMiss(hb) {
    this.nearMisses++;
    this.score += 40 * this.comboMult();
    this._addCombo(2);
    const pos = this._calloutPos();
    this.fx.text(pick(SLANG_NEAR), pos.x + 30, pos.y - 24, "#ff9f1c", 32);
    this.fx.burst(hb.x + hb.w / 2, hb.y, 10, "#ffe14d", 230, 380);
    this.triggerShake(3, 0.12);
    Audio_.whoosh();
  }

  /* ---------------- update ---------------- */
  update(dt) {
    if (this.state !== "PLAYING") return;
    dt = Math.min(dt, 0.05);
    this.time += dt;

    this.dayNight.update(dt);
    this.weather.update(dt, this.speed);

    // Quantum Taxi ride: temporary speed boost on top of the normal curve
    if (this.rideTimer > 0) { this.rideTimer -= dt; if (this.rideTimer <= 0) this._endTaxiRide(); }
    this.rideBoost = lerp(this.rideBoost, this.rideTimer > 0 ? (this.player.rideKind === "board" ? 1.3 : 1.45) : 1, clamp(dt * 2.5, 0, 1));

    this.speed = lerp(this.speed, this.targetSpeed(), dt * 0.6);
    const spd = this.speed * this.rideBoost * this._shopWorldMul();   // effective world speed this frame
    const distDelta = (spd * dt) / PX_PER_METER;
    this.distance += distDelta;

    if (this.magnetTimer > 0) this.magnetTimer -= dt;
    if (this.multiTimer > 0) this.multiTimer -= dt;
    if (this.bootsTimer > 0) this.bootsTimer -= dt;
    this.player.hasBoots = this.bootsTimer > 0;

    this.player.worldSpeed = spd;
    this.player.update(dt);
    if (this.player.landImpact) {
      if (this.player.landImpact > 450) this.fx.dust(PLAYER_X + 10, GROUND_Y - 2, 7, -1);
      this.player.landImpact = 0;
    }
    if (this.player.grounded) {
      this.dustTimer -= dt;
      if (this.dustTimer <= 0) { this.fx.dust(PLAYER_X - 8, GROUND_Y - 2, 1, -1); this.dustTimer = 0.11; }
    }

    if (this.combo > 0) {
      this.comboTimer -= dt;
      if (this.comboTimer <= 0) this._dropCombo(false);
    }
    if (this.comboFlash > 0) this.comboFlash = Math.max(0, this.comboFlash - dt * 4);

    this.bgScrollA -= spd * 0.22 * dt;
    this.bgScrollB -= spd * 0.55 * dt;

    this.spawnTimer -= dt;
    if (this.spawnTimer <= 0) {
      // no new obstacles while the Sospana Sonke shop is on its way in, so the door is always reachable
      if (this.shop && !this.shop.used && this.shop.x > PLAYER_X - 200) this.spawnTimer = 0.3;
      else {
        this.spawnPattern();
        const tier = this.difficultyTier();
        const gapPx = (tier === 0 ? rand(640, 820) : tier === 1 ? rand(540, 700) : tier === 2 ? rand(460, 620) : rand(420, 560)) * DIFF().gapMul;
        this.spawnTimer = Math.max(0.5, gapPx / Math.max(spd, 120));
      }
    }
    this.powerupTimer -= dt;
    if (this.powerupTimer <= 0) { this.maybeSpawnPowerup(); this.powerupTimer = rand(12, 18) * DIFF().powerupMul; }

    this.pedTimer -= dt;
    if (this.pedTimer <= 0) {
      // spawn off-screen on one of the two pavement lanes; keep a gap so nobody overlaps a walker in the same lane
      const lane = Math.random() < 0.5 ? 0 : 1, x = CW + 90;
      if (this.ambientPeds.length < 7 && !this.ambientPeds.some(a => a.lane === lane && a.x > x - 170)) this.ambientPeds.push(new AmbientPed(x, lane));
      this.pedTimer = rand(1.8, 4.2);
    }

    this.taxiTimer -= dt;
    if (this.taxiTimer <= 0) { this.ambientTaxis.push(new AmbientTaxi(CW + 60)); this.taxiTimer = rand(9, 16); if (Math.random()<0.4) Audio_.honk(); }

    this.animalTimer -= dt;
    if (this.animalTimer <= 0) {
      const kind = Math.random() < 0.65 ? "goat" : "cow";
      const n = kind === "goat" ? randInt(2, 3) : 1;
      for (let i = 0; i < n; i++) this.animals.push(new AmbientAnimal(CW + 50 + i * 36, kind));
      this.animalTimer = rand(22, 40);
    }

    this.bgPropTimer -= dt;
    if (this.bgPropTimer <= 0) {
      const last = this.bgProps[this.bgProps.length - 1];
      const startX = last ? last.x + rand(150, 230) : CW + 60;
      this.bgProps.push(new BackgroundProp(startX, this._propSeed++));
      this.bgPropTimer = rand(0.9, 1.5) * (260 / spd);
    }
    this.poleTimer -= dt;
    if (this.poleTimer <= 0) {
      const lastPole = this.poles[this.poles.length - 1];
      if (lastPole) lastPole.span = (CW + 40) - lastPole.x;     // wires run on to the next pole
      this.poles.push(new DecorPole(CW + 40));
      this.poleTimer = rand(2.6, 3.6) * (260 / spd);
    }

    for (const o of this.obstacles) o.update(dt, spd);
    for (const h of this.hazards) h.update(dt, spd);
    for (const c of this.collectibles) c.update(dt, spd, (this.magnetTimer > 0 || this.rideTimer > 0) ? this.player.hitbox : null);
    for (const p of this.powerups) p.update(dt, spd);
    for (const b of this.bgProps) b.update(dt, spd * 0.55);
    for (const tp of this.townProps) tp.update(dt, spd * 0.7);
    for (const pl of this.poles) pl.update(dt, spd * 0.85);
    for (const sg of this.signs) sg.update(dt, spd * 0.85);
    for (const ap of this.ambientPeds) ap.update(dt, spd);
    for (const at of this.ambientTaxis) at.update(dt, spd);
    for (const an of this.animals) an.update(dt, spd);
    this.fx.update(dt, spd);
    this._updateExtras(dt, spd);

    this.obstacles = this.obstacles.filter(o => !o.dead);
    this.hazards = this.hazards.filter(h => !h.dead);
    this.collectibles = this.collectibles.filter(c => !c.dead && !c.collected);
    this.powerups = this.powerups.filter(p => !p.dead);
    this.bgProps = this.bgProps.filter(b => b.x > -220);
    this.townProps = this.townProps.filter(t => t.x + t.w / 2 > -40);
    this._fillTownRow();
    this.poles = this.poles.filter(p => p.x + Math.min(p.span, 1200) > -40);   // keep a pole until its wires have left the screen
    this.ambientPeds = this.ambientPeds.filter(a => a.x > -110);
    this.ambientTaxis = this.ambientTaxis.filter(a => a.x > -160);
    this.animals = this.animals.filter(a => a.x > -80);
    this.signs = this.signs.filter(s => s.x > -170);

    this._checkCollisions();
    this._updateNearMiss(this.player.hitbox);

    this.score += distDelta * 1.0 * (this.multiTimer > 0 ? 2 : 1);
    this._triggerZoneBanner();

    // Stage change (painted background switches) -> dramatic transition
    const bgKey = this.currentBgKey();
    if (bgKey !== this.lastBgKey) this._startStageTransition(bgKey);
    if (this.bgFade < 1) {
      if (IMAGES[this.lastBgKey] && IMAGES[this.lastBgKey].width) this.bgFade = Math.min(1, this.bgFade + dt / 1.4);   // wait for the new plate to be ready
      if (this.bgFade >= 1) { this.bgPrevKey = null; PlateStore.keep([this.lastBgKey, Journey.slot(Journey.slotAt(this.distance).n + 1).area.key]); }
    }
    if (this.stageFx) { this.stageFx.t += dt; if (this.stageFx.t >= this.stageFx.dur) this.stageFx = null; }
    if (this.flash > 0) this.flash = Math.max(0, this.flash - dt * 1.8);

    if (this.distance >= this.milestoneNext) {
      this.score += 250;
      Audio_.milestone();
      const idx = Math.floor(this.milestoneNext / 500) - 1;
      const m = this.milestoneNext;
      this._pushBanner({ text: (m >= 1000 && m % 1000 === 0 ? (m / 1000) + " KM!" : m + "m!"), sub: fmtHero(MILESTONE_LINES[idx % MILESTONE_LINES.length]) + "  +250", dur: 2.2, kind: "milestone" });
      this.fx.confetti(CW / 2, 150, 34, 400);
      this.triggerShake(4, 0.25);
      this.milestoneNext += 500;
    }

    // banner queue
    if (this.banner) {
      this.banner.t += dt;
      if (this.banner.t >= this.banner.dur) this.banner = this.bannerQueue.shift() || null;
    }

    if (this.shakeTime > 0) this.shakeTime -= dt;

    UI.updateStats({
      dist: Math.floor(this.distance), cash: this.cash, score: Math.floor(this.score * DIFF().scoreMul),
      lives: this.player.lives, shield: this.player.shield,
      magnet: this.magnetTimer > 0, multi: this.multiTimer > 0, boots: this.bootsTimer > 0,
      taxi: this.rideTimer > 0 && this.player.rideKind === "taxi",
      board: this.rideTimer > 0 && this.player.rideKind === "board",
      ammo: this.ammo, shopNear: this._shopNear()
    });

    if (this.player.lives <= 0) this.gameOver();
  }

  _checkCollisions() {
    const pbox = this.player.hitbox;
    const riding = this.rideTimer > 0;
    // while riding the taxi, anything in front of the bonnet gets smashed
    const sbox = riding ? { x: pbox.x, y: pbox.y, w: pbox.w + 40, h: pbox.h } : pbox;

    for (const o of this.obstacles) {
      if (aabbOverlap(sbox, o.hitbox)) {
        if (riding) this._smash(o);
        else { this._hitPlayer(); o.dead = true; }
      }
    }
    for (const h of this.hazards) {
      if (aabbOverlap(sbox, h.hitbox)) {
        if (riding) this._smash(h);
        else { this._hitPlayer(); h.dead = true; }
      }
    }
    for (const c of this.collectibles) {
      if (!c.collected && aabbOverlap(pbox, c.hitbox)) {
        const def = COLLECTIBLE_DEFS[c.type];
        const mult = this.comboMult();
        if (c.type === "heart") {
          if (this.player.lives < MAX_LIVES) { this.player.lives++; Audio_.heartPickup(); }
          else { this.cash += Math.round(30 * DIFF().cashMul); this.score += 15; Audio_.coin(); }
          this.fx.burst(c.x, c.y, 10, "#ff6b8a", 200, 200);
          this.fx.text("+1 life", c.x, c.y - 30, "#ff8aa5", 24);
        } else {
          const cashMult = this.multiTimer > 0 ? 2 : 1;
          this.cash += Math.round(def.value * cashMult * DIFF().cashMul);
          this.score += def.score * mult;
          if (c.type === "moneybag") { Audio_.bigCash(); this.fx.burst(c.x, c.y, 16, "#7cff6b", 280); this.triggerShake(2, 0.12); this._addCombo(2); }
          else if (c.type === "gem") { Audio_.gem(); this.fx.burst(c.x, c.y, 12, "#63e6ff", 260); this.triggerShake(2, 0.1); this._addCombo(1); }
          else if (c.type === "star") { Audio_.coin(); this.fx.burst(c.x, c.y, 12, "#fff2a0", 250); this._addCombo(1); }
          else { Audio_.coin(); this.fx.burst(c.x, c.y, 6, "#ffd23f", 170); this._addCombo(1); }
        }
        c.collected = true;
      }
    }
    for (const p of this.powerups) {
      if (aabbOverlap(pbox, p.hitbox)) {
        p.dead = true;
        Audio_.powerup();
        this.fx.burst(p.x, p.y, 16, POWERUP_DEFS[p.kind].color, 280);
        if (p.kind === "shield") this.player.shield = true;
        else if (p.kind === "magnet") this.magnetTimer = 8;
        else if (p.kind === "multi") this.multiTimer = 10;
        else if (p.kind === "boots") this.bootsTimer = 12;
        else if (p.kind === "taxi") { this._startTaxiRide(); continue; }
        else if (p.kind === "board") { this._startBoard(); continue; }
        else if (p.kind === "gun") { this._giveAmmo(); continue; }
        UI.flashZoneBanner(`${POWERUP_DEFS[p.kind].icon} ${POWERUP_DEFS[p.kind].label}!`);
      }
    }
  }

  /* ---------------- rendering ---------------- */
  render() {
    const ctx = this.ctx;
    ctx.save();
    ctx.clearRect(0, 0, CW, CH);

    if (this.shakeTime > 0) {
      const m = this.shakeMag * (this.shakeTime / (this.shakeDur || 0.3));
      ctx.translate(rand(-m, m), rand(-m, m));
    }

    const night = this._nightAmt();
    this._drawSky(ctx);
    this._drawFar(ctx, night);
    this._drawBackgroundArt(ctx);
    this._drawBgRow(ctx);
    for (const tp of this.townProps) Town.drawProp(ctx, tp, TOWN_BASE_Y, this.time, night);
    for (const at of this.ambientTaxis) at.draw(ctx);
    this._drawRoad(ctx);
    for (const ap of this.ambientPeds.slice().sort((a, b) => a.y - b.y)) ap.draw(ctx);
    for (const an of this.animals) an.draw(ctx);
    if (this.shop) ShopArt.draw(ctx, this.shop, GROUND_Y + 2, night, this.time, this._shopNear());

    for (const pl of this.poles) pl.draw(ctx);
    for (const sg of this.signs) sg.draw(ctx);

    for (const c of this.collectibles) c.draw(ctx);
    for (const p of this.powerups) p.draw(ctx);
    for (const h of this.hazards) h.draw(ctx);
    for (const o of this.obstacles) o.draw(ctx);

    this.player.draw(ctx);
    for (const s of this.shots) s.draw(ctx);
    this._drawJumpPips(ctx);
    this.fx.drawWorld(ctx);
    this._drawSpeedLines(ctx);

    this.weather.draw(ctx);
    this._drawNightOverlay(ctx);
    this._drawAmbientLift(ctx);
    this._drawTownLights(ctx, night);
    this._drawVignette(ctx);

    ctx.restore();

    // overlays that should not shake
    this._drawStageFx(ctx);
    this._drawBanner(ctx);
    this._drawComboHud(ctx);
    this.fx.drawTexts(ctx);
  }

  _nightAmt() { return clamp((this.dayNight.phase() - 0.45) / 0.3, 0, 1); }

  _drawFar(ctx, night) {
    const yTop = 58;                       // base of the skyline tucks behind the painted scene
    const scroll = this.bgScrollA * 0.5;
    const pal = this.townPalFor(this.currentBgKey());
    if (this.bgFade < 1 && this.bgPrevKey) {
      Town.drawFar(ctx, this.townPalFor(this.bgPrevKey), scroll, 1, night, yTop);
      Town.drawFar(ctx, pal, scroll, this.bgFade, night, yTop);
    } else {
      Town.drawFar(ctx, pal, scroll, 1, night, yTop);
    }
  }

  _drawTownLights(ctx, night) {
    ctx.save();
    ctx.globalCompositeOperation = "lighter";
    for (const tp of this.townProps) Town.drawLights(ctx, tp, TOWN_BASE_Y, this.time, night);
    if (this.shop) ShopArt.drawGlow(ctx, this.shop, GROUND_Y + 2, night, this.time);
    if (night > 0.05) {
      // minibus headlights on the ambient taxis
      const h = Town.haloSprite("255,240,170");
      ctx.globalAlpha = night * 0.8;
      for (const at of this.ambientTaxis) ctx.drawImage(h, at.x + 36 - 28, 396 - 9 - 28, 56, 56);
    }
    ctx.restore();
  }

  _drawSpeedLines(ctx) {
    const inten = clamp((this.speed * this.rideBoost - 340) / 200, 0, 1) + (this.rideTimer > 0 ? 0.5 : 0);
    if (inten <= 0.05 || this.state === "MENU") return;
    const n = Math.floor(4 + inten * 10);
    ctx.save();
    ctx.strokeStyle = "rgba(255,255,255," + (0.07 + inten * 0.1).toFixed(3) + ")";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const y = 60 + ((i * 97.3) % (CH - 120));
      const len = 50 + inten * 90 + (i % 3) * 20;
      const x = CW - (((this.time * (700 + (i % 4) * 160)) + i * 131) % (CW + 300)) + 100;
      ctx.moveTo(x, y); ctx.lineTo(x + len, y);
    }
    ctx.stroke();
    ctx.restore();
  }

  _drawStageFx(ctx) {
    if (this.flash > 0) {
      ctx.save();
      ctx.globalAlpha = Math.min(0.7, this.flash * 0.7);
      ctx.fillStyle = "#fff4c8";
      ctx.fillRect(0, 0, CW, CH);
      ctx.restore();
    }
    const f = this.stageFx;
    if (!f) return;
    const k = f.t / f.dur;
    const P = Town.PALETTES[f.pal];
    // colourful sweeping curtain (Ndebele-style stripes) wiping across the screen
    if (k < 0.6) {
      const u = k / 0.6, e = u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
      const cx = lerp(-200, CW + 200, e), bw = 54;
      ctx.save();
      ctx.globalAlpha = 0.92 * (1 - Math.abs(u - 0.5) * 0.4);
      for (let i = -3; i <= 3; i++) {
        ctx.fillStyle = P.accent[(i + 3) % 5];
        ctx.beginPath();
        const x0 = cx + i * bw;
        ctx.moveTo(x0 + 70, 0); ctx.lineTo(x0 + 70 + bw, 0); ctx.lineTo(x0 + bw, CH); ctx.lineTo(x0, CH); ctx.closePath(); ctx.fill();
      }
      ctx.restore();
    }
    // radial speed-burst lines
    if (k < 0.5) {
      ctx.save();
      ctx.globalAlpha = (1 - k / 0.5) * 0.55;
      ctx.strokeStyle = "#fff"; ctx.lineWidth = 2;
      ctx.beginPath();
      for (let i = 0; i < 22; i++) {
        const a = (i / 22) * Math.PI * 2 + 0.1, r0 = 70 + k * 500, r1 = r0 + 140;
        ctx.moveTo(CW / 2 + Math.cos(a) * r0, CH / 2 + Math.sin(a) * r0 * 0.7);
        ctx.lineTo(CW / 2 + Math.cos(a) * r1, CH / 2 + Math.sin(a) * r1 * 0.7);
      }
      ctx.stroke();
      ctx.restore();
    }
  }

  _drawBanner(ctx) {
    const b = this.banner;
    if (!b) return;
    const k = b.t / b.dur;
    const ease = (x) => 1 - Math.pow(1 - x, 3);
    let off = 0;
    if (k < 0.16) off = -(1 - ease(k / 0.16)) * (CW + 60);
    else if (k > 0.84) off = Math.pow((k - 0.84) / 0.16, 2) * (CW + 60);
    const y = Math.round(CH * 0.27), h = 74;
    const pal = Town.PALETTES[this.townPalFor(this.currentBgKey())];
    ctx.save();
    ctx.translate(off, 0);
    const g = ctx.createLinearGradient(0, y - h / 2, 0, y + h / 2);
    g.addColorStop(0, "rgba(30,10,8,0.92)"); g.addColorStop(1, "rgba(60,20,12,0.92)");
    ctx.fillStyle = g; ctx.fillRect(0, y - h / 2, CW, h);
    // zig-zag Ndebele border top and bottom
    for (let i = 0, x = 0; x < CW; x += 14, i++) {
      ctx.fillStyle = pal.accent[i % 5];
      ctx.beginPath(); ctx.moveTo(x, y - h / 2); ctx.lineTo(x + 14, y - h / 2); ctx.lineTo(x + 7, y - h / 2 + 8); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(x, y + h / 2); ctx.lineTo(x + 14, y + h / 2); ctx.lineTo(x + 7, y + h / 2 - 8); ctx.closePath(); ctx.fill();
    }
    ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.lineJoin = "round";
    const big = b.kind === "milestone" ? "#ffd23f" : b.kind === "taxi" ? "#5ad1ff" : b.kind === "shop" ? "#7cff8a" : b.kind === "board" ? "#2ec4b6" : "#ffffff";
    ctx.font = "900 34px 'Segoe UI', Arial, sans-serif";
    ctx.lineWidth = 6; ctx.strokeStyle = "rgba(0,0,0,0.9)";
    ctx.strokeText(b.text, CW / 2, y - 8); ctx.fillStyle = big; ctx.fillText(b.text, CW / 2, y - 8);
    ctx.font = "800 15px 'Segoe UI', Arial, sans-serif";
    ctx.lineWidth = 4; ctx.strokeText(b.sub, CW / 2, y + 20); ctx.fillStyle = "#f4e9d8"; ctx.fillText(b.sub, CW / 2, y + 20);
    ctx.restore();
  }

  _drawComboHud(ctx) {
    if (this.combo < 2 || this.state === "MENU") return;
    const mult = this.comboMult();
    const cols = ["#ffd23f", "#ffd23f", "#ff9f1c", "#ff5a3c", "#ff3d9a", "#b46bff"];
    const col = cols[mult];
    const sc = 1 + this.comboFlash * 0.2;
    ctx.save();
    ctx.translate(CW / 2, 86);
    ctx.scale(sc, sc);
    ctx.fillStyle = "rgba(0,0,0,0.55)";
    ctx.beginPath(); ctx.roundRect(-82, -17, 164, 34, 17); ctx.fill();
    ctx.lineWidth = 2; ctx.strokeStyle = col; ctx.stroke();
    ctx.textBaseline = "middle";
    ctx.textAlign = "left"; ctx.font = "800 13px 'Segoe UI', Arial, sans-serif"; ctx.fillStyle = "#fff";
    ctx.fillText("COMBO " + this.combo, -70, 0);
    ctx.textAlign = "right"; ctx.font = "900 22px 'Segoe UI', Arial, sans-serif"; ctx.fillStyle = col;
    ctx.fillText("x" + mult, 72, 1);
    // time-left bar
    ctx.fillStyle = "rgba(255,255,255,0.18)"; ctx.fillRect(-70, 11, 140, 3);
    ctx.fillStyle = col; ctx.fillRect(-70, 11, 140 * clamp(this.comboTimer / 3.4, 0, 1), 3);
    ctx.restore();
  }

  _drawSky(ctx) {
    const { top, bot } = this.dayNight.skyColors();
    const grad = ctx.createLinearGradient(0, 0, 0, GROUND_Y);
    grad.addColorStop(0, rgbStr(top));
    grad.addColorStop(1, rgbStr(bot));
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, CW, GROUND_Y + 40);

    const night = this.dayNight.isNight();
    ctx.save();
    ctx.globalAlpha = 0.9;
    ctx.fillStyle = night ? "#eef0ff" : "#fff2c2";
    ctx.shadowColor = night ? "#c9d3ff" : "#ffdd88";
    ctx.shadowBlur = 26;
    ctx.beginPath();
    ctx.arc(760, 90, night ? 22 : 30, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    if (night) {
      ctx.save();
      ctx.fillStyle = "rgba(255,255,255,0.75)";
      for (let i = 0; i < 40; i++) {
        const sx = (i * 137.5) % CW;
        const sy = (i * 71.3) % (GROUND_Y - 60);
        ctx.globalAlpha = 0.3 + 0.5 * (((i * 53) % 10) / 10);
        ctx.fillRect(sx, sy, 2, 2);
      }
      ctx.restore();
    }
  }

  _drawBackgroundArt(ctx) {
    const key = this.currentBgKey();
    let img = IMAGES[key];
    if (!img || !img.width) { PlateStore.ensure(key); img = IMAGES[this.bgPrevKey] || IMAGES[this.lastBgKey]; }
    if (!img || !img.width) return;
    const h = 300;
    const w = (img.width / img.height) * h;
    const y = GROUND_Y - h + 40;
    let x = this.bgScrollA % w;
    if (x > 0) x -= w;
    ctx.save();
    // stage transition: cross-fade from the previous painted scene
    const prev = this.bgFade < 1 && this.bgPrevKey ? IMAGES[this.bgPrevKey] : null;
    if (prev && prev.width) {
      const pw = (prev.width / prev.height) * h;
      let px = this.bgScrollA % pw; if (px > 0) px -= pw;
      ctx.globalAlpha = 0.92;
      for (let dx = px; dx < CW + pw; dx += pw) ctx.drawImage(prev, dx, y, pw, h);
    }
    ctx.globalAlpha = 0.92 * (prev && prev.width ? this.bgFade : 1);
    for (let dx = x; dx < CW + w; dx += w) ctx.drawImage(img, dx, y, w, h);
    ctx.restore();

    // Color-grade overlay for later laps (see bgMood()) — re-tints the same
    // 3 paintings so a long run keeps looking fresh.
    const mood = this.bgMood();
    if (mood) {
      ctx.save();
      ctx.globalCompositeOperation = mood.op;
      ctx.fillStyle = mood.color;
      ctx.fillRect(0, y, CW, h);
      ctx.restore();
    }
  }

  _drawBgRow(ctx) {
    const rowY = 396;
    ctx.save();
    for (const b of this.bgProps) b.draw(ctx, rowY);
    ctx.restore();
  }

  _drawRoad(ctx) {
    // pavement strip
    ctx.fillStyle = "#b0a898";
    ctx.fillRect(0, GROUND_Y - 24, CW, 24);
    ctx.fillStyle = "rgba(0,0,0,0.08)";
    for (let x = (this.bgScrollB % 40); x < CW; x += 40) ctx.fillRect(x, GROUND_Y - 24, 2, 24);

    // road
    const roadGrad = ctx.createLinearGradient(0, GROUND_Y, 0, CH);
    roadGrad.addColorStop(0, "#6a655b");
    roadGrad.addColorStop(1, "#46413a");
    ctx.fillStyle = roadGrad;
    ctx.fillRect(0, GROUND_Y, CW, CH - GROUND_Y);

    // lane dashes
    ctx.fillStyle = "rgba(255,214,90,0.55)";
    const dashW = 34, gap = 26;
    const dashP = dashW + gap;
    let x = (this.bgScrollB / PAVE_K) % dashP; if (x > 0) x -= dashP;       // scrolls at exactly the world speed
    for (; x < CW; x += dashP) ctx.fillRect(x, GROUND_Y + 26, dashW, 5);

    // decorative potholes
    ctx.fillStyle = "rgba(0,0,0,0.28)";
    for (let i = 0; i < 5; i++) {
      const M = CW + 200, px = ((((i * 260 + this.bgScrollB / PAVE_K) % M) + M) % M) - 100;
      const py = GROUND_Y + 46 + (i % 3) * 8;
      ctx.beginPath();
      ctx.ellipse(px, py, 20, 7, 0, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  _drawNightOverlay(ctx) {
    const p = this.dayNight.phase();
    if (p > 0.15) {
      ctx.save();
      ctx.globalAlpha = clamp((p - 0.3) / 0.7, 0, 0.15);     // was up to 0.55 of near-black
      ctx.fillStyle = "#3c418a";
      ctx.fillRect(0, 0, CW, CH);
      ctx.restore();
    }
  }

  // Ambient light lift: a gentle additive warm wash so nothing ever gets murky.
  _drawAmbientLift(ctx) {
    const p = this.dayNight.phase();
    ctx.save();
    ctx.globalCompositeOperation = "lighter";
    ctx.fillStyle = "rgba(255," + (232 - p * 36 | 0) + "," + (196 - p * 56 | 0) + "," + (0.10 + 0.07 * p).toFixed(3) + ")";
    ctx.fillRect(0, 0, CW, CH);
    ctx.restore();
  }

  _drawVignette(ctx) {
    const g = ctx.createRadialGradient(CW/2, CH/2, CH*0.35, CW/2, CH/2, CH*0.9);
    g.addColorStop(0, "rgba(0,0,0,0)");
    g.addColorStop(1, "rgba(0,0,0,0.14)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, CW, CH);
  }
}

/* ---------------------------------------------------------
   UI / DOM WIRING
--------------------------------------------------------- */
const UI = (function () {
  const el = (id) => document.getElementById(id);
  const screens = ["loadingScreen","startScreen","howtoScreen","pauseScreen","gameOverScreen","rotateHint","creditsScreen"];

  function hideAllScreens() { screens.forEach(id => el(id).classList.add("hidden")); }
  function show(id) { el(id).classList.remove("hidden"); }
  function hide(id) { el(id).classList.add("hidden"); }

  function showHUD(v) {
    if (v) { el("hud").classList.remove("hidden"); el("touchControls").classList.remove("hidden"); }
    else { el("hud").classList.add("hidden"); el("touchControls").classList.add("hidden"); }
  }

  let zoneBannerTO = null;
  function flashZoneBanner(text) {
    const b = el("zoneBanner");
    b.textContent = text;
    b.classList.add("show");
    clearTimeout(zoneBannerTO);
    zoneBannerTO = setTimeout(() => b.classList.remove("show"), 1700);
  }
  function setZone(name) { el("zoneLabel").textContent = name; }
  const REGION_COL = ["#2bb6c4", "#ffd23f", "#ff7a59", "#a47be0", "#5fd16a"];
  let journeyBuilt = false, journeyLast = -1;
  function setJourney(n, N, lap, name, regionIdx) {
    const box = el("journey"); if (!box) return;
    if (!journeyBuilt) {
      const strip = el("journeyStrip"); strip.innerHTML = "";
      AREAS.forEach((a) => { const i = document.createElement("i"); i.style.background = REGION_COL[a.regionIdx]; strip.appendChild(i); });
      journeyBuilt = true;
    }
    const ticks = el("journeyStrip").children;
    for (let i = 0; i < ticks.length; i++) ticks[i].className = i < n - 1 ? "done" : i === n - 1 ? "now" : "";
    el("journeyTxt").textContent = "Gauteng journey " + n + "/" + N + (lap > 1 ? " · lap " + lap : "") + " · " + name;
    journeyLast = n;
  }
  function setHero(name) { const b = el("heroBadge"); if (b) b.textContent = name; }

  function updateStats({ dist, cash, score, lives, shield, magnet, multi, boots, taxi, board, ammo, shopNear }) {
    el("distVal").textContent = dist;
    el("cashVal").textContent = cash;
    el("scoreVal").textContent = score;
    const heartsEl = el("lives");
    let hearts = "";
    const shown = Math.max(DIFF().lives, lives);
    if (shown > 6) hearts = "❤️ ×" + lives;
    else for (let i = 0; i < shown; i++) hearts += i < lives ? "❤️" : "🖤";
    if (shield) hearts += " 🛡️";
    heartsEl.textContent = hearts;

    const bar = el("powerupBar");
    bar.innerHTML = "";
    if (magnet) bar.innerHTML += `<div class="powerup-chip">🧲 MAGNET</div>`;
    if (boots) bar.innerHTML += `<div class="powerup-chip">🚀 BOOTS</div>`;
    if (multi) bar.innerHTML += `<div class="powerup-chip">⚡ x2</div>`;
    if (taxi) bar.innerHTML += `<div class="powerup-chip">🚕 TAXI RIDE</div>`;
    if (board) bar.innerHTML += `<div class="powerup-chip">🛹 SKATEBOARD</div>`;
    if (ammo > 0) bar.innerHTML += `<div class="powerup-chip">💥 BLASTER ${ammo}</div>`;
    const fb = el("fireBtn"), eb = el("enterBtn");
    if (fb) fb.classList.toggle("hidden", !(ammo > 0));
    if (eb) eb.classList.toggle("hidden", !shopNear);
  }

  function showGameOver({ level, dist, cash, score, bestDist, bestCash, isNewBest, combo, near }) {
    hideAllScreens();
    el("goDist").textContent = dist;
    el("goCash").textContent = cash;
    el("goScore").textContent = score;
    el("goBestDist").textContent = bestDist;
    if (el("goCombo")) el("goCombo").textContent = combo || 0;
    if (el("goNear")) el("goNear").textContent = near || 0;
    el("newHighBadge").classList.toggle("hidden", !isNewBest);
    const hn = heroName();
    const titles = ["Caught Slippin'!", hn + "'s Down But Not Out!", "Gauteng Wins This Round!", "Hustle Interrupted!", hn + " Needs a Breather!"];
    el("gameOverTitle").textContent = pick(titles);
    if (el("goHero")) el("goHero").textContent = hn + " ran " + dist + " m";
    const LV = DIFFICULTY[level] || DIFF();
    if (el("goLevel")) { el("goLevel").textContent = LV.label + " level" + (LV.scoreMul !== 1 ? " · score x" + LV.scoreMul : ""); el("goLevel").style.color = LV.color; }
    show("gameOverScreen");
  }

  function refreshMenuBest() {
    const b = readBest(DIFF_KEY);
    el("menuBest").textContent = b.dist;
    el("menuBestCash").textContent = b.cash;
    if (el("menuBestLevel")) el("menuBestLevel").textContent = DIFF().label;
  }
  function setDiff() {          // HUD badge: the level of the current run
    const b = el("diffBadge"); if (!b) return;
    const L = DIFF(); b.textContent = L.label; b.style.color = L.color; b.style.borderColor = L.color;
  }

  function setMuteLabel() { el("muteBtn").textContent = Audio_.isMuted() ? "🔇 SOUND" : "🔊 SOUND"; }

  return { hideAllScreens, show, hide, showHUD, flashZoneBanner, setZone, setJourney, setHero, updateStats, showGameOver, refreshMenuBest, setMuteLabel, setDiff };
})();

/* ---------------------------------------------------------
   BOOT
--------------------------------------------------------- */
window.addEventListener("DOMContentLoaded", async () => {
  const canvas = document.getElementById("game");
  setupInput(canvas);

  const game = new Game(canvas);
  window.__bvhGame = game;
  window.__bvhDebug = { DIFFICULTY, DIFF, readBest, getDiffKey: () => DIFF_KEY, AREAS, Journey, REGIONS, WALK_META, AmbientPed, WALK_LANES, RUNMETA, CHARACTERS, CHAR_ORDER, PlateStore, SPRITES, AreaSign, areaStart, areaAt, areaIndexAt, loadCharacter, heroName, Obstacle, MovingHazard, Collectible, PowerUp, Player, IMAGES, aabbOverlap, OBSTACLE_TYPES, AmbientTaxi, AmbientPed, BackgroundProp, DecorPole, TallStack, GuptaArt, Shop, Shot, ShopArt, USE_CARTOON_GUPTA, Town, FX, TownProp, AmbientAnimal, GAME_VERSION, getCW: () => CW, getCH: () => CH };

  const cardsEl = document.getElementById("charSelect");
  function setCreditsHero() {
    const ch = CHARACTERS[CURRENT_CHAR], el = document.getElementById("creditsHero"), nm = document.getElementById("creditsStar");
    if (nm) nm.textContent = ch.name;
    if (el) { el.alt = ch.name; el.onerror = () => { try { el.src = GuptaArt.portrait(240, 320, { state: "idle", t: 0.6 }); } catch (e) {} }; el.src = ch.portrait; }
  }
  /* ---------------- difficulty select (remembered) ---------------- */
  const diffEl = document.getElementById("diffSelect");
  function refreshDiffUI() {
    if (diffEl) diffEl.querySelectorAll(".diff-btn").forEach(b => { const on = b.dataset.diff === DIFF_KEY; b.classList.toggle("selected", on); b.setAttribute("aria-checked", on ? "true" : "false"); });
    const dd = document.getElementById("diffDesc"); if (dd) { dd.textContent = DIFF().blurb; dd.style.color = DIFF().color; }
    UI.refreshMenuBest(); UI.setDiff();
    const cl = document.getElementById("creditsLevel"); if (cl) { cl.textContent = DIFF().label; cl.style.color = DIFF().color; }
  }
  function setDiffKey(k) {
    if (!DIFFICULTY[k] || game.state === "PLAYING") return;
    DIFF_KEY = k;
    try { localStorage.setItem(DIFF_STORE, k); } catch (e) {}
    game.best = readBest(k);
    refreshDiffUI();
  }
  window.__bvhSetDiff = setDiffKey;
  if (diffEl) diffEl.querySelectorAll(".diff-btn").forEach(b => b.addEventListener("click", () => { Audio_.click(); setDiffKey(b.dataset.diff); }));
  function refreshCharUI() {
    const ch = CHARACTERS[CURRENT_CHAR];
    cardsEl.querySelectorAll(".char-card").forEach(b => { const on = b.dataset.char === CURRENT_CHAR; b.classList.toggle("selected", on); b.setAttribute("aria-checked", on ? "true" : "false"); b.tabIndex = on ? 0 : -1; });
    const pb = document.getElementById("playBtn"); if (pb) pb.textContent = "▶ RUN AS " + ch.name;
    const sn = document.getElementById("selName"); if (sn) sn.textContent = ch.name;
    const st = document.getElementById("selTag"); if (st) st.textContent = ch.tag;
    document.querySelectorAll(".hero-name-txt").forEach(n => { n.textContent = ch.name; });
    setCreditsHero();
    UI.setHero(ch.name);
  }
  async function selectChar(id) {
    if (!CHARACTERS[id]) return;
    CURRENT_CHAR = id;
    try { localStorage.setItem(CHAR_KEY, id); } catch (e) {}
    refreshCharUI();
    await loadCharacter(id);
  }
  window.__bvhSelectChar = selectChar;
  function buildCharSelect() {
    cardsEl.innerHTML = "";
    CHAR_ORDER.forEach((id, i) => {
      const ch = CHARACTERS[id];
      const b = document.createElement("button");
      b.type = "button"; b.className = "char-card"; b.dataset.char = id; b.setAttribute("role", "radio");
      b.style.setProperty("--cc", ch.color);
      b.innerHTML = '<span class="char-pic"><img alt="" draggable="false"></span><span class="char-name"></span><span class="char-tag"></span><span class="char-key">' + (i + 1) + '</span>';
      b.querySelector(".char-name").textContent = ch.name; b.querySelector(".char-tag").textContent = ch.tag;
      const img = b.querySelector("img"); img.alt = ch.name;
      img.addEventListener("error", () => {
        if (ch.kind === "sheet" && !img.dataset.fb) { img.dataset.fb = "1"; try { img.src = GuptaArt.portrait(180, 240, { state: "idle", t: 0.6 }); return; } catch (e) {} }
        img.style.visibility = "hidden";
      });
      img.src = ch.portrait;
      b.addEventListener("click", () => { Audio_.click(); selectChar(id); });
      cardsEl.appendChild(b);
    });
    refreshCharUI();
  }
  function cycleChar(d) {
    const i = CHAR_ORDER.indexOf(CURRENT_CHAR);
    selectChar(CHAR_ORDER[(i + d + CHAR_ORDER.length) % CHAR_ORDER.length]);
  }

  await loadAllAssets((frac) => {
    const pct = Math.round(frac * 100);
    document.getElementById("loadbar").style.width = pct + "%";
    document.getElementById("loadingText").textContent = `Loading the hustle… ${pct}%`;
  });

  const verEl = document.getElementById("gameVersion");
  if (verEl) verEl.textContent = "v" + GAME_VERSION;
  buildCharSelect();
  refreshDiffUI();
  await Promise.all([loadCharacter(CURRENT_CHAR), PlateStore.ensure(AREAS[0].key)]);
  PlateStore.ensure(AREAS[1].key);
  CHAR_ORDER.forEach(id => { if (id !== CURRENT_CHAR) loadCharacter(id); });     // warm the other two while on the menu
  UI.refreshMenuBest();
  UI.setMuteLabel();
  UI.hideAllScreens();
  UI.show("startScreen");
  game.state = "MENU";

  function checkOrientation() {
    const isMobile = Math.min(window.innerWidth, window.innerHeight) < 700;
    const isPortrait = window.innerHeight > window.innerWidth;
    if (isMobile && isPortrait && !sessionStorage.getItem("bvh_rotate_seen")) {
      UI.show("rotateHint");
      sessionStorage.setItem("bvh_rotate_seen", "1");
    }
  }
  setTimeout(checkOrientation, 600);

  /* ---------------- Input wiring (double jump + hold-for-height) ---------------- */
  Input.on((action) => {
    Audio_.unlock();
    if (game.state === "PLAYING") {
      if (action === "fire") game._fire();
      else if (action === "enter") game.tryEnterShop();
      else if (action === "jumpDown") game.player.jumpDown();
      else if (action === "jumpUp") game.player.jumpUp();
      else if (action === "pause") doPause();
    }
  });

  document.getElementById("touchJump").addEventListener("touchstart", (e) => {
    e.preventDefault(); Audio_.unlock();
    if (game.state === "PLAYING") game.player.jumpDown();
  }, { passive: false });
  document.getElementById("touchJump").addEventListener("touchend", (e) => {
    e.preventDefault();
    if (game.state === "PLAYING") game.player.jumpUp();
  }, { passive: false });
  document.getElementById("touchJump").addEventListener("mousedown", () => {
    if (game.state === "PLAYING") game.player.jumpDown();
  });
  document.getElementById("touchJump").addEventListener("mouseup", () => {
    if (game.state === "PLAYING") game.player.jumpUp();
  });

  /* ---------------- On-screen action buttons (FIRE / ENTER SHOP) ---------------- */
  function bindAction(id, fn) {
    const b = document.getElementById(id);
    if (!b) return;
    b.addEventListener("pointerdown", (e) => { e.preventDefault(); e.stopPropagation(); Audio_.unlock(); if (game.state === "PLAYING") fn(); });
    b.addEventListener("touchstart", (e) => { e.stopPropagation(); }, { passive: true });
    b.addEventListener("click", (e) => e.preventDefault());
  }
  bindAction("fireBtn", () => game._fire());
  bindAction("enterBtn", () => game.tryEnterShop());

  /* ---------------- Credits ---------------- */
  let creditsFrom = "start";
  function openCredits(from) {
    creditsFrom = from || "start";
    { const L = DIFFICULTY[game.runDiff || DIFF_KEY] || DIFF(), cl = document.getElementById("creditsLevel"); if (cl) { cl.textContent = L.label; cl.style.color = L.color; } }
    UI.hideAllScreens();
    const roll = document.getElementById("creditsRoll");
    roll.style.animation = "none"; void roll.offsetWidth; roll.style.animation = "";
    UI.show("creditsScreen");
  }
  function closeCredits() {
    UI.hide("creditsScreen");
    if (creditsFrom === "gameover" && game.state === "GAMEOVER") UI.show("gameOverScreen");
    else { game.state = "MENU"; UI.refreshMenuBest(); UI.show("startScreen"); }
  }
  window.__bvhOpenCredits = openCredits;
  document.getElementById("creditsBtn").addEventListener("click", () => { Audio_.click(); openCredits("start"); });
  document.getElementById("creditsBtn2").addEventListener("click", () => { Audio_.click(); clearTimeout(game._creditsTimer); openCredits("gameover"); });
  document.getElementById("creditsBack").addEventListener("click", () => { Audio_.click(); closeCredits(); });
  document.getElementById("creditsRoll").addEventListener("animationend", closeCredits);

  /* ---------------- Buttons ---------------- */
  function doPause() {
    if (game.state !== "PLAYING") return;
    game.state = "PAUSED";
    UI.show("pauseScreen");
  }
  function doResume() { UI.hide("pauseScreen"); game.state = "PLAYING"; }

  async function playNow() { Audio_.unlock(); Audio_.click(); await loadCharacter(CURRENT_CHAR); await PlateStore.ensure(AREAS[0].key); game.startRun(); }
  document.getElementById("playBtn").addEventListener("click", playNow);
  window.addEventListener("keydown", (e) => {          // character select with the keyboard
    const open = (id) => !document.getElementById(id).classList.contains("hidden");
    if (!open("startScreen") || open("howtoScreen") || open("creditsScreen") || open("rotateHint") || game.state === "PLAYING") return;
    if (e.key === "ArrowLeft" || e.code === "KeyA") { e.preventDefault(); cycleChar(-1); }
    else if (e.key === "ArrowRight" || e.code === "KeyD") { e.preventDefault(); cycleChar(1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setDiffKey(DIFF_ORDER[Math.max(0, DIFF_ORDER.indexOf(DIFF_KEY) - 1)]); }
    else if (e.key === "ArrowDown") { e.preventDefault(); setDiffKey(DIFF_ORDER[Math.min(2, DIFF_ORDER.indexOf(DIFF_KEY) + 1)]); }
    else if (e.key === "1" || e.key === "2" || e.key === "3") selectChar(CHAR_ORDER[+e.key - 1]);
    else if (e.key === "Enter") {
      const t = e.target;
      if (t && t.tagName === "BUTTON" && !t.classList.contains("char-card") && t.id !== "playBtn") return;
      e.preventDefault(); playNow();
    }
  });
  document.getElementById("howtoBtn").addEventListener("click", () => { Audio_.click(); UI.show("howtoScreen"); });
  document.getElementById("closeHowto").addEventListener("click", () => { Audio_.click(); UI.hide("howtoScreen"); });
  document.getElementById("muteBtn").addEventListener("click", () => { Audio_.setMuted(!Audio_.isMuted()); UI.setMuteLabel(); });
  document.getElementById("pauseBtn").addEventListener("click", doPause);
  document.getElementById("resumeBtn").addEventListener("click", doResume);
  document.getElementById("restartBtnPause").addEventListener("click", () => { Audio_.click(); UI.hide("pauseScreen"); game.startRun(); });
  document.getElementById("quitBtn").addEventListener("click", () => {
    Audio_.click(); game.state = "MENU"; UI.hideAllScreens(); UI.showHUD(false); UI.refreshMenuBest(); UI.show("startScreen");
  });
  document.getElementById("retryBtn").addEventListener("click", () => { Audio_.click(); game.startRun(); });
  document.getElementById("menuBtn").addEventListener("click", () => {
    Audio_.click(); clearTimeout(game._creditsTimer); game.state = "MENU"; UI.hideAllScreens(); UI.refreshMenuBest(); UI.show("startScreen");
  });
  document.getElementById("rotateDismiss").addEventListener("click", () => UI.hide("rotateHint"));

  document.addEventListener("visibilitychange", () => {
    if (document.hidden && game.state === "PLAYING") doPause();
  });

  /* ---------------- Main loop ---------------- */
  let last = performance.now();
  function loop(now) {
    const dt = Math.min((now - last) / 1000, 0.05);
    last = now;
    if (game.state === "PLAYING") game.update(dt);
    game.render();
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
});

})();
