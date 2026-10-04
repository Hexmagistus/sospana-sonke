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

  it("the pre-hydration script applies the same rule, so there is no dark flash", () => {
    for (const p of ENTRY_FLOW_PATHS) assert.ok(THEME_BOOTSTRAP_SCRIPT.includes(`"${p}"`), p);
    assert.match(THEME_BOOTSTRAP_SCRIPT, /theme = 'light'/);
    assert.match(THEME_BOOTSTRAP_SCRIPT, /location\.pathname/);
  });
});
