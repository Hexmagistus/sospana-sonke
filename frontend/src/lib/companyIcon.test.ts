import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, it } from "node:test";
import { companyIconSrc } from "./companyIcon.js";

const API = "https://api.example.com/api/v1";

describe("company icon requests", () => {
  it("never requests an icon the API says it does not have", () => {
    assert.equal(companyIconSrc(API, "c1", false, 123), null);
    assert.equal(companyIconSrc(API, "c1", undefined), null);
    assert.equal(companyIconSrc(API, null, true, 123), null);
    assert.equal(companyIconSrc(API, "", true), null);
  });

  it("puts the icon version in the URL so it can be cached as immutable", () => {
    assert.equal(companyIconSrc(API, "c1", true, 1791280910), `${API}/companies/c1/icon?v=1791280910`);
    assert.equal(companyIconSrc(API, "c1", true, 0), `${API}/companies/c1/icon?v=0`);
  });

  it("falls back to the plain URL without a usable version", () => {
    assert.equal(companyIconSrc(API, "c1", true), `${API}/companies/c1/icon`);
    assert.equal(companyIconSrc(API, "c1", true, null), `${API}/companies/c1/icon`);
    assert.equal(companyIconSrc(API, "c1", true, Number.NaN), `${API}/companies/c1/icon`);
    assert.equal(companyIconSrc(API, "c1", true, -5), `${API}/companies/c1/icon`);
  });

  it("escapes the id", () => {
    assert.equal(companyIconSrc(API, "a/b?c", true), `${API}/companies/a%2Fb%3Fc/icon`);
  });

  it("the logo image is lazy-loaded and keeps the monogram fallback", () => {
    const logo = readFileSync(join(process.cwd(), "src", "components", "CompanyLogo.tsx"), "utf8");
    assert.match(logo, /loading="lazy"/);
    assert.match(logo, /companyIconSrc\(/);
    assert.match(logo, /onError=\{/);
    assert.match(logo, /ss-monogram/);
    // /companies has its own cards; the group pages (universities, colleges, hospitals,
    // ngos, government) all render components/GroupDirectory.tsx.
    for (const file of [["app", "companies", "page.tsx"], ["components", "GroupDirectory.tsx"]]) {
      const src = readFileSync(join(process.cwd(), "src", ...file), "utf8");
      assert.match(src, /hasIcon=\{!!c\.has_icon\}/, file.join("/"));
      assert.match(src, /iconVersion=\{c\.icon_version\}/, file.join("/"));
    }
  });
});
