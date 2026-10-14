import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { LIST_OFFSET_MAX, LIST_PAGE, listOffset } from "./listWindow.js";

describe("public list paging", () => {
  it("keeps offset 550 instead of jumping back to the first page", () => {
    assert.equal(listOffset("550"), 550);
    assert.equal(listOffset("500"), 500);
    assert.equal(listOffset(String(LIST_OFFSET_MAX)), LIST_OFFSET_MAX - (LIST_OFFSET_MAX % LIST_PAGE));
  });

  it("treats a page past the cap as the first page", () => {
    assert.equal(listOffset(String(LIST_OFFSET_MAX + LIST_PAGE)), 0);
    assert.equal(listOffset("-10"), 0);
    assert.equal(listOffset("nope"), 0);
  });
});
