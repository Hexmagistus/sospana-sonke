#!/usr/bin/env node
/**
 * Phone-fit check: no sideways scroll and no clipped content at 320, 360, 375, 390 and 414px.
 *
 * For every page and width it asserts
 *   1. document.documentElement.scrollWidth <= window.innerWidth   (no horizontal scroll), and
 *   2. no text, button, input or image sticks out of the box that clips it (content cut off
 *      by an overflow:hidden parent does not scroll, so check 1 alone would miss it).
 * Boxes that scroll on purpose (overflow:auto/scroll) and marquee/decorative nodes are exempt.
 *
 * Not part of CI (it needs a running site and a browser). Run it against a local or preview build:
 *
 *   npm i --no-save playwright-core
 *   BASE_URL=http://localhost:3000 CHROME_PATH=/usr/bin/google-chrome node scripts/mobile-fit.mjs
 *
 * Logged-in pages are checked when API_URL, TEST_EMAIL and TEST_PASSWORD are set
 * (use a throwaway account on a local or staging stack, never a real person's):
 *
 *   API_URL=http://localhost:8000/api/v1 TEST_EMAIL=a@b.test TEST_PASSWORD=... node scripts/mobile-fit.mjs
 *
 * Optional: PAGES="/,/login" to limit the list, WIDTHS="320,390".
 * Exit code 1 when any page fails.
 */
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require("playwright-core"));
} catch {
  console.error("playwright-core is not installed. Run: npm i --no-save playwright-core");
  process.exit(2);
}

const BASE = (process.env.BASE_URL || "http://localhost:3000").replace(/\/$/, "");
const WIDTHS = (process.env.WIDTHS || "320,360,375,390,414").split(",").map(Number);
const PUBLIC_PAGES = ["/", "/login", "/register", "/forgot-password", "/reset-password", "/terms", "/privacy", "/donate", "/donate/thanks"];
const AUTH_PAGES = [
  "/dashboard", "/agent", "/applications", "/companies", "/companies?country=ZA", "/universities", "/colleges",
  "/hospitals", "/coverage", "/master-cv", "/profile", "/preferences", "/messages", "/notifications",
  "/security", "/subscription", "/matches", "/tailor", "/tailor/applications",
];

const SCROLL_JS = () => ({ sw: document.documentElement.scrollWidth, w: window.innerWidth });

const CLIPPED_JS = () => {
  const out = [];
  const clipper = (e) => {
    for (let p = e.parentElement; p; p = p.parentElement) {
      const o = getComputedStyle(p).overflowX;
      if (o === "hidden" || o === "clip" || o === "auto" || o === "scroll") return p;
    }
    return null;
  };
  for (const e of document.querySelectorAll("body *")) {
    const cs = getComputedStyle(e);
    if (cs.position === "fixed") continue;
    if (e.closest('.animate-marquee,[aria-hidden="true"]')) continue;
    if (cs.position === "absolute" && e.classList.contains("select-none")) continue;
    const r = e.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    const hasText = [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    if (!hasText && !["IMG", "BUTTON", "A", "INPUT", "SELECT"].includes(e.tagName)) continue;
    const box = clipper(e);
    if (!box) continue;
    const ox = getComputedStyle(box).overflowX;
    if (ox === "auto" || ox === "scroll") continue; // a scroller on purpose
    const b = box.getBoundingClientRect();
    if (r.right > b.right + 1 || r.left < b.left - 1) {
      out.push(`${e.tagName.toLowerCase()} "${(e.textContent || "").trim().slice(0, 30)}" ${Math.round(r.left)}..${Math.round(r.right)} in box ${Math.round(b.left)}..${Math.round(b.right)}`);
    }
  }
  return out.slice(0, 5);
};

async function tokens() {
  const { API_URL, TEST_EMAIL, TEST_PASSWORD } = process.env;
  if (!API_URL || !TEST_EMAIL || !TEST_PASSWORD) return null;
  const res = await fetch(`${API_URL.replace(/\/$/, "")}/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: TEST_EMAIL, password: TEST_PASSWORD }),
  });
  if (!res.ok) throw new Error(`Login failed with HTTP ${res.status}`);
  return res.json();
}

const only = process.env.PAGES ? process.env.PAGES.split(",") : null;
const auth = await tokens();
const browser = await chromium.launch({
  executablePath: process.env.CHROME_PATH || undefined,
  args: ["--no-sandbox"],
});

const failures = [];
let checked = 0;
for (const loggedIn of [false, true]) {
  if (loggedIn && !auth) continue;
  const pages = (loggedIn ? AUTH_PAGES : PUBLIC_PAGES).filter((p) => !only || only.includes(p));
  for (const width of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width, height: 800 }, isMobile: true, hasTouch: true });
    if (loggedIn) {
      await ctx.addInitScript(([a, r]) => {
        localStorage.setItem("sospana_access_token", a);
        localStorage.setItem("sospana_refresh_token", r);
        localStorage.setItem("ss-directory-guide", "hidden");
      }, [auth.access_token, auth.refresh_token]);
    }
    const page = await ctx.newPage();
    for (const path of pages) {
      await page.goto(BASE + path, { waitUntil: "networkidle", timeout: 60000 });
      await page.waitForTimeout(1200);
      const { sw, w } = await page.evaluate(SCROLL_JS);
      const clipped = await page.evaluate(CLIPPED_JS);
      checked += 1;
      if (sw > w) failures.push(`${path} @${width}px: scrollWidth ${sw} > ${w}`);
      for (const c of clipped) failures.push(`${path} @${width}px: clipped ${c}`);
    }
    await ctx.close();
  }
}
await browser.close();

console.log(`mobile-fit: ${checked} page/width checks${auth ? "" : " (public pages only; set API_URL/TEST_EMAIL/TEST_PASSWORD for logged-in pages)"}`);
if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
console.log("mobile-fit: OK");
