import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  NOT_COUNTED_INLINE,
  NOT_COUNTED_LABEL,
  NOT_COUNTED_NOTICE_BODY,
  NOT_COUNTED_NOTICE_TITLE,
  NOT_COUNTED_TOOLTIP,
  anyNotCounted,
  isNotCounted,
} from "./notCounted.js";

const link = "https://example.org/careers";

describe("isNotCounted follows the card rule", () => {
  it("is true with a careers link and no known count", () => {
    assert.equal(isNotCounted({ careers_url: link }), true);
    assert.equal(isNotCounted({ careers_url: link, open_vacancies: 0, open_vacancies_known: false }), true);
  });
  it("is false for a known count, a real zero, or held vacancies", () => {
    assert.equal(isNotCounted({ careers_url: link, open_vacancies: 0, open_vacancies_known: true }), false);
    assert.equal(isNotCounted({ careers_url: link, open_vacancies: 3, open_vacancies_known: false }), false);
  });
  it("is false when there is no careers link (the card shows nothing)", () => {
    assert.equal(isNotCounted({ careers_url: null }), false);
    assert.equal(isNotCounted({ careers_url: "" }), false);
  });
  it("anyNotCounted drives the list notice", () => {
    assert.equal(anyNotCounted([]), false);
    assert.equal(anyNotCounted([{ careers_url: link, open_vacancies: 2, open_vacancies_known: true }]), false);
    assert.equal(
      anyNotCounted([
        { careers_url: link, open_vacancies: 2, open_vacancies_known: true },
        { careers_url: link, open_vacancies: 0, open_vacancies_known: false },
      ]),
      true,
    );
  });
});

describe("disclaimer wording", () => {
  it("says it is not the same as no vacancies and tells clients to check the employer", () => {
    assert.equal(NOT_COUNTED_LABEL, "Not counted yet");
    for (const text of [NOT_COUNTED_TOOLTIP, NOT_COUNTED_NOTICE_BODY]) {
      assert.match(text, /automated reading/);
      assert.match(text, /cannot (count|read)/);
      assert.match(text, /directly/);
      assert.match(text, /careers link/);
    }
    assert.match(NOT_COUNTED_NOTICE_BODY, /keep checking/);
    assert.match(NOT_COUNTED_TOOLTIP, /does not mean/);
    assert.match(NOT_COUNTED_NOTICE_TITLE, /does not mean/);
    assert.match(NOT_COUNTED_INLINE, /Check their site/);
  });
});
