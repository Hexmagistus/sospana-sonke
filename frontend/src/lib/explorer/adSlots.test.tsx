import "./testPaths";
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { AdSlot, LoginAdRail } from "./AdSlot";
import { AdApplyForm } from "./AdApplyForm";
import { isExplorerPath } from "./explorerPaths";
import {
  EMPTY_FORM, LOGIN_SLOT_KEYS, MIN_NOTE, NO_PAYMENT_NOTE, SLOT_COUNT, SLOT_LABELS, isLoginSlotKey, parseAmount, safeHref, slotKeys, toPayload, totalUsd, validateAdForm,
  type AdForm, type PublicAd,
} from "./adSlots";

const good: AdForm = {
  businessName: "Mabena Plumbing", email: "owner@mabena.example", website: "https://mabena.example",
  adText: "Plumbing across Gauteng", amount: "1", days: "7",
};

describe("ad slots", () => {
  it("there are only four spots, LG1-LG4, two each side of the sign-in form", () => {
    assert.equal(SLOT_COUNT, 4);
    assert.deepEqual([...LOGIN_SLOT_KEYS], ["LG1", "LG2", "LG3", "LG4"]);
    assert.deepEqual(slotKeys("left"), ["LG1", "LG2"]);
    assert.deepEqual(slotKeys("right"), ["LG3", "LG4"]);
    for (const k of LOGIN_SLOT_KEYS) assert.ok(k.length <= 4 && SLOT_LABELS[k].startsWith("Spot "), k);
  });

  it("old explorer keys are not login spots", () => {
    for (const k of ["LG1", "LG4"]) assert.equal(isLoginSlotKey(k), true, k);
    for (const k of ["L1", "R10", "LG5", "LG0", "", null, undefined]) assert.equal(isLoginSlotKey(k as string), false, String(k));
  });

  it("an empty slot says Advertise here and offers Apply for this spot", () => {
    const out = renderToStaticMarkup(createElement(AdSlot, { slotKey: "LG3", onApply: () => {} }));
    assert.match(out, /Advertise here/);
    assert.match(out, />Apply for this spot</);
    assert.match(out, /aria-label="Advertise here: apply for spot LG3"/);
    assert.doesNotMatch(out, />Sponsored</);
  });

  it("an approved ad renders labelled Sponsored with rel sponsored noopener", () => {
    const ad: PublicAd = { slot_key: "LG2", business_name: "Mabena Plumbing", ad_text: "Plumbing across Gauteng", website: "https://mabena.example" };
    const out = renderToStaticMarkup(createElement(AdSlot, { slotKey: "LG2", ad, onApply: () => {} }));
    assert.match(out, /Sponsored/);
    assert.match(out, /rel="sponsored noopener"/);
    assert.match(out, /href="https:\/\/mabena\.example\/"/);
    assert.match(out, /Mabena Plumbing/);
    assert.doesNotMatch(out, /Advertise here/);
  });

  it("an ad with a non-http link is never linked", () => {
    const ad: PublicAd = { slot_key: "LG2", business_name: "X", ad_text: "y", website: "javascript:alert(1)" };
    const out = renderToStaticMarkup(createElement(AdSlot, { slotKey: "LG2", ad, onApply: () => {} }));
    assert.doesNotMatch(out, /javascript:/);
    assert.match(out, /Advertise here/);
    assert.equal(safeHref("javascript:alert(1)"), null);
    assert.equal(safeHref("ftp://x.example"), null);
  });

  it("a rail renders its two spots, visible at every width, all empty without ads", () => {
    const out = renderToStaticMarkup(createElement(LoginAdRail, { side: "right", ads: [], onApply: () => {} }));
    assert.deepEqual([...out.matchAll(/data-slot="([^"]+)"/g)].map((m) => m[1]), ["LG3", "LG4"]);
    assert.equal((out.match(/Advertise here</g) ?? []).length, 2);
    assert.doesNotMatch(out, /\bhidden\b/);
    assert.doesNotMatch(out, />Sponsored</);
  });

  it("a rail puts an approved ad only in its own spot", () => {
    const ad: PublicAd = { slot_key: "LG1", business_name: "Bee Co", ad_text: "Honey", website: "https://bee.example" };
    const left = renderToStaticMarkup(createElement(LoginAdRail, { side: "left", ads: [ad], onApply: () => {} }));
    const right = renderToStaticMarkup(createElement(LoginAdRail, { side: "right", ads: [ad], onApply: () => {} }));
    assert.equal((left.match(/Advertise here</g) ?? []).length, 1);
    assert.equal((left.match(/>Sponsored</g) ?? []).length, 1);
    assert.doesNotMatch(right, />Sponsored</);
  });
});

describe("minimum $1/day", () => {
  it("accepts exactly $1 and above", () => {
    assert.deepEqual(validateAdForm(good), {});
    assert.deepEqual(validateAdForm({ ...good, amount: "2.50" }), {});
    assert.deepEqual(validateAdForm({ ...good, amount: "2,50" }), {});
  });

  it("rejects anything under $1, zero, negatives and non-numbers", () => {
    for (const bad of ["0.99", "0.5", "0", "-1", "", "abc", "1.234"]) {
      const e = validateAdForm({ ...good, amount: bad });
      assert.ok(e.amount, `amount ${bad} should be refused`);
    }
    assert.match(validateAdForm({ ...good, amount: "0.99" }).amount ?? "", /minimum is \$1 per day/);
  });

  it("parseAmount only reads plain amounts", () => {
    assert.equal(parseAmount("1"), 1);
    assert.equal(parseAmount(" 2.5 "), 2.5);
    assert.ok(Number.isNaN(parseAmount("1e3")));
  });

  it("totals amount times days and gives nothing for an invalid amount", () => {
    assert.equal(totalUsd({ ...good, amount: "2.5", days: "10" }), 25);
    assert.equal(totalUsd({ ...good, amount: "0.5" }), null);
  });

  it("validates the other fields", () => {
    assert.ok(validateAdForm({ ...good, email: "nope" }).email);
    assert.ok(validateAdForm({ ...good, website: "nodots" }).website);
    assert.ok(validateAdForm({ ...good, adText: "x".repeat(121) }).adText);
    assert.ok(validateAdForm({ ...good, days: "0" }).days);
    assert.ok(validateAdForm(EMPTY_FORM).businessName);
  });

  it("the payload carries the amount as two decimals and the chosen slot", () => {
    assert.deepEqual(toPayload(good, "LG3"), {
      business_name: "Mabena Plumbing", contact_email: "owner@mabena.example", website: "https://mabena.example",
      ad_text: "Plumbing across Gauteng", amount_usd_per_day: "1.00", days: 7, requested_slot: "LG3",
    });
  });
});

describe("application form", () => {
  const out = renderToStaticMarkup(createElement(AdApplyForm, { slotKey: "LG4", onClose: () => {}, submit: async () => { throw new Error("no"); } }));

  it("has every field, the minimum on the amount input, and the honest notes", () => {
    for (const label of ["Business name", "Contact email", "Website", "Short ad text", "Amount per day \\(USD\\)", "Number of days"]) {
      assert.match(out, new RegExp(`>${label}<`));
    }
    assert.match(out, /type="number"[^>]*min="1"/);
    assert.ok(out.includes(MIN_NOTE.replace("$", "$")));
    assert.ok(out.includes("payment instructions follow by email"));
    assert.ok(NO_PAYMENT_NOTE.includes("does not charge"));
    assert.match(out, /sign-in page, in one of four spots/);
  });

  it("lets the advertiser pick one of the four login spots, preselecting the one clicked", () => {
    assert.match(out, />Spot</);
    assert.match(out, /<option value="">Any free spot<\/option>/);
    assert.deepEqual([...out.matchAll(/<option value="(LG\d)"/g)].map((m) => m[1]), ["LG1", "LG2", "LG3", "LG4"]);
    assert.match(out, /<option value="LG4" selected="">/);
    const legacy = renderToStaticMarkup(createElement(AdApplyForm, { slotKey: "R5", onClose: () => {}, submit: async () => { throw new Error("no"); } }));
    assert.match(legacy, /<option value="" selected="">Any free spot/);
    assert.doesNotMatch(legacy, /R5/);
  });

  it("does not claim an exact running cost", () => {
    assert.doesNotMatch(out, /costs? (us )?\$\d/i);
    assert.match(out, /roughly/);
  });
});

describe("explorer paths", () => {
  it("only the six explorer pages drop the desktop top bar", () => {
    for (const p of ["/companies", "/universities", "/colleges", "/hospitals", "/ngos", "/government", "/companies/"]) assert.equal(isExplorerPath(p), true, p);
    for (const p of ["/dashboard", "/", "/admin", "/companies/x", "/coverage", null, undefined]) assert.equal(isExplorerPath(p as string), false, String(p));
  });
});
