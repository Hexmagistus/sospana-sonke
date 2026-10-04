import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ThemeToggleButton, { BRIGHTNESS_LABEL, brightnessHint } from "./ThemeToggleButton.js";

const render = (theme: "light" | "dark", className?: string) =>
  renderToStaticMarkup(createElement(ThemeToggleButton, { theme, onToggle: () => {}, className }));

describe("brightness toggle caption", () => {
  for (const theme of ["light", "dark"] as const) {
    it(`shows "Adjust brightness" under the icon in ${theme} mode`, () => {
      const html = render(theme);
      assert.equal(BRIGHTNESS_LABEL, "Adjust brightness");
      assert.match(html, /<span[^>]*data-testid="theme-toggle-label"[^>]*>Adjust brightness<\/span>/);
      // the icon comes first, the caption after it
      assert.ok(html.indexOf("<svg") < html.indexOf("Adjust brightness</span>"));
      assert.match(html, /flex-col/);
    });

    it(`keeps the caption visible at every width and readable in ${theme} mode`, () => {
      const html = render(theme);
      const label = /<span[^>]*data-testid="theme-toggle-label"[^>]*>/.exec(html)![0];
      assert.ok(!/\bhidden\b|max-\w+:hidden|sr-only/.test(label), "caption must never be hidden");
      // 0.7rem (12.25px at the 17.5px root) is the floor; never a px size under 12
      assert.match(label, /text-\[0\.7rem\]/);
      assert.ok(!/text-\[(?:[0-9]|1[01])px\]/.test(label));
      // coloured by the themed token that themeContrast.test.ts checks in light and dark
      assert.match(label, /text-ss-primary/);
    });
  }

  it("still announces the action to screen readers and is a real button", () => {
    assert.match(render("light"), /<button type="button"[^>]*aria-label="Adjust brightness\. Switch to dark mode"/);
    assert.match(render("dark"), /aria-label="Adjust brightness\. Switch to light mode"/);
    assert.equal(brightnessHint("dark"), "Adjust brightness. Switch to light mode");
  });

  it("is narrow enough for a 320px phone top bar", () => {
    assert.match(render("light"), /w-\[3\.6rem\]/);
  });
});
