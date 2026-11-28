import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { ENTRY_FLOW_PATHS, effectiveTheme, isEntryFlowPath } from "./entryFlow.js";
import { THEME_BOOTSTRAP_SCRIPT } from "./themeBootstrap.js";

describe("entry flow is always bright", () => {
  it("covers landing, login, register, forgot and reset password", () => {
    for (const p of ["/", "/login", "/register", "/forgot-password", "/reset-password", "/login/", "/reset-password/"]) {
      assert.equal(isEntryFlowPath(p), true, p);
    }
  });

  it("leaves the app pages to the visitor's choice", () => {
    for (const p of ["/companies", "/dashboard", "/tailor", "/privacy", "/admin", "/loginx", "", null, undefined]) {
      assert.equal(isEntryFlowPath(p as string), false, String(p));
    }
  });

  it("forces light on entry pages even when dark is stored, and keeps dark elsewhere", () => {
    assert.equal(effectiveTheme("/", "dark"), "light");
    assert.equal(effectiveTheme("/register", "dark"), "light");
    assert.equal(effectiveTheme("/companies", "dark"), "dark");
    assert.equal(effectiveTheme("/companies", "light"), "light");
  });

  it("the pre-hydration script always forces light (light-only site)", () => {
    assert.match(THEME_BOOTSTRAP_SCRIPT, /setAttribute\('data-theme', 'light'\)/);
    assert.doesNotMatch(THEME_BOOTSTRAP_SCRIPT, /'dark'/);
  });
});
