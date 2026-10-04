import "./testPaths";
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { AdColumn, AdSlot } from "./AdSlot";
import { AdApplyForm } from "./AdApplyForm";
import { isExplorerPath } from "./explorerPaths";
import {
  EMPTY_FORM, MIN_NOTE, NO_PAYMENT_NOTE, SLOTS_PER_SIDE, parseAmount, safeHref, slotKeys, toPayload, totalUsd, validateAdForm,
  type AdForm, type PublicAd,
} from "./adSlots";

const good: AdForm = {
  businessName: "Mabena Plumbing", email: "owner@mabena.example", website: "https://mabena.example",
  adText: "Plumbing across Gauteng", amount: "1", days: "7",
};

describe("ad slots", () => {
  it("each side has ten keys, left L1-L10 and right R1-R10", () => {
    assert.equal(SLOTS_PER_SIDE, 10);
    assert.deepEqual(slotKeys("L"), ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10"]);
    assert.equal(slotKeys("R")[9], "R10");
  });

  it("an empty slot says Your ad here and offers Apply for this spot", () => {
    const out = renderToStaticMarkup(createElement(AdSlot, { slotKey: "L3", onApply: () => {} }));
    assert.match(out, /Your ad here/);
    assert.match(out, />Apply for this spot</);
    assert.doesNotMatch(out, /Sponsored/);
  });

  it("an approved ad renders labelled Sponsored with rel sponsored noopener", () => {
    const ad: PublicAd = { slot_key: "R2", business_name: "Mabena Plumbing", ad_text: "Plumbing across Gauteng", website: "https://mabena.example" };
    const out = renderToStaticMarkup(createElement(AdSlot, { slotKey: "R2", ad, onApply: () => {} }));
    assert.match(out, /Sponsored/);
    assert.match(out, /rel="sponsored noopener"/);
    assert.match(out, /href="https:\/\/mabena\.example\/"/);
    assert.match(out, /Mabena Plumbing/);
    assert.doesNotMatch(out, /Your ad here/);
  });

  it("an ad with a non-http link is never linked", () => {
    const ad: PublicAd = { slot_key: "R2", business_name: "X", ad_text: "y", website: "javascript:alert(1)" };
    const out = renderToStaticMarkup(createElement(AdSlot, { slotKey: "R2", ad, onApply: () => {} }));
    assert.doesNotMatch(out, /javascript:/);
    assert.match(out, /Your ad here/);
    assert.equal(safeHref("javascript:alert(1)"), null);
    assert.equal(safeHref("ftp://x.example"), null);
  });

  it("a column renders ten slots, hidden below xl, and with no ads they are all empty", () => {
    const out = renderToStaticMarkup(createElement(AdColumn, { side: "L", ads: [], onApply: () => {} }));
    assert.equal((out.match(/Your ad here/g) ?? []).length, 10);
    assert.match(out, /class="hidden xl:block"/);
    assert.doesNotMatch(out, /Sponsored/);
  });

  it("a column puts an approved ad only in its own slot", () => {
    const ad: PublicAd = { slot_key: "L4", business_name: "Bee Co", ad_text: "Honey", website: "https://bee.example" };
    const out = renderToStaticMarkup(createElement(AdColumn, { side: "L", ads: [ad], onApply: () => {} }));
    assert.equal((out.match(/Your ad here/g) ?? []).length, 9);
    assert.equal((out.match(/Sponsored/g) ?? []).length, 1);
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
    assert.deepEqual(toPayload(good, "L3"), {
      business_name: "Mabena Plumbing", contact_email: "owner@mabena.example", website: "https://mabena.example",
      ad_text: "Plumbing across Gauteng", amount_usd_per_day: "1.00", days: 7, requested_slot: "L3",
    });
  });
});

describe("application form", () => {
  const out = renderToStaticMarkup(createElement(AdApplyForm, { slotKey: "R5", onClose: () => {}, submit: async () => { throw new Error("no"); } }));

  it("has every field, the minimum on the amount input, and the honest notes", () => {
    for (const label of ["Business name", "Contact email", "Website", "Short ad text", "Amount per day \\(USD\\)", "Number of days"]) {
      assert.match(out, new RegExp(`>${label}<`));
    }
    assert.match(out, /type="number"[^>]*min="1"/);
    assert.ok(out.includes(MIN_NOTE.replace("$", "$")));
    assert.ok(out.includes("payment instructions follow by email"));
    assert.ok(NO_PAYMENT_NOTE.includes("does not charge"));
    assert.match(out, /spot R5/);
  });

  it("does not claim an exact running cost", () => {
    assert.doesNotMatch(out, /costs? (us )?\$\d/i);
    assert.match(out, /roughly/);
  });
});

describe("explorer paths", () => {
  it("only the three explorer pages drop the desktop top bar", () => {
    for (const p of ["/companies", "/universities", "/hospitals", "/companies/"]) assert.equal(isExplorerPath(p), true, p);
    for (const p of ["/colleges", "/dashboard", "/", "/admin", "/companies/x", null, undefined]) assert.equal(isExplorerPath(p as string), false, String(p));
  });
});
