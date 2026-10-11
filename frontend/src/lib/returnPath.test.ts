import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { safeInternalPath } from "./returnPath.js";

describe("sign-in return path", () => {
  it("keeps a directory or country path on this site", () => {
    assert.equal(safeInternalPath("/companies?country=ZA"), "/companies?country=ZA");
    assert.equal(safeInternalPath("/countries/south-africa"), "/countries/south-africa");
    assert.equal(safeInternalPath("/countries"), "/countries");
  });

  it("drops other sites, protocol-relative paths, and the rest of the app", () => {
    assert.equal(safeInternalPath("https://evil.example/companies"), null);
    assert.equal(safeInternalPath("//evil.example/companies"), null);
    assert.equal(safeInternalPath("/login"), null);
    assert.equal(safeInternalPath("/admin"), null);
    assert.equal(safeInternalPath("companies"), null);
    assert.equal(safeInternalPath(null), null);
  });
});
