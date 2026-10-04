import "./testPaths";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, it } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { BalungileWalker } from "./BalungileWalker";
import { HowToUseCard } from "./HowToUseCard";

const html = (props: Parameters<typeof BalungileWalker>[0]) => renderToStaticMarkup(createElement(BalungileWalker, props));

describe("BalungileWalker", () => {
  it("renders only while loading", () => {
    assert.equal(html({ loading: false }), "");
    assert.match(html({ loading: true }), /data-balungile/);
  });

  it("has a polite status caption and hides the drawing from screen readers", () => {
    const out = html({ loading: true });
    assert.match(out, /<p role="status" aria-live="polite"[^>]*>Loading employers…<\/p>/);
    assert.match(out, /<div aria-hidden="true" class="ss-bal-track">/);
    assert.match(html({ loading: true, label: "Loading hospitals…" }), />Loading hospitals…<\/p>/);
  });

  it("walks by default and holds a still pose, caption kept, when motion is reduced", () => {
    assert.match(html({ loading: true, reducedMotion: false }), /data-motion="walk"/);
    const still = html({ loading: true, reducedMotion: true });
    assert.match(still, /data-motion="reduced"/);
    assert.match(still, /role="status"/);
  });
});

describe("HowToUseCard hook-in", () => {
  const steps = ["One", "Two"];
  const card = (loading?: boolean, initialOpen = true) =>
    renderToStaticMarkup(createElement(HowToUseCard, { steps, initialOpen, loading }));

  it("shows Balungile directly below the card only while loading", () => {
    const loading = card(true);
    assert.ok(loading.indexOf("</section>") < loading.indexOf("data-balungile"));
    assert.ok(!card(false).includes("data-balungile"));
    assert.ok(!card().includes("data-balungile"));
  });

  it("also shows her under the collapsed How to use button", () => {
    const out = card(true, false);
    assert.ok(out.indexOf("</button>") < out.indexOf("data-balungile"));
  });
});

describe("Balungile art and CSS", () => {
  const png = readFileSync(join(process.cwd(), "public", "balungile-walk.png"));
  const css = readFileSync(join(process.cwd(), "src", "app", "globals.css"), "utf8");

  it("ships her eight-frame strip (58x94 per frame, 464x94)", () => {
    assert.equal(png.subarray(1, 4).toString(), "PNG");
    assert.equal(png.readUInt32BE(16), 58 * 8);
    assert.equal(png.readUInt32BE(20), 94);
  });

  it("steps through eight frames, paces both ways, flips at each end and stops for reduced motion", () => {
    assert.match(css, /animation: ss-bal-frames [\d.]+s steps\(8\) infinite/);
    assert.match(css, /@keyframes ss-bal-pace \{ 0%, 100% \{ left: 0; \} 50% \{ left: calc\(100% - var\(--bw\)\); \} \}/);
    assert.match(css, /@keyframes ss-bal-turn \{ 0% \{ transform: scaleX\(1\); \} 50% \{ transform: scaleX\(-1\); \} \}/);
    assert.match(css, /@media \(prefers-reduced-motion: reduce\) \{\s*\.ss-bal-pace, \.ss-bal-turn, \.ss-bal-sprite \{ animation: none !important; \}/);
  });
});
