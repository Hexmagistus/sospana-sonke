import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { FLAGSHIP_COUNTRY, flagshipCountry, flagshipQuery } from "./flagship.js";

describe("flagship country", () => {
  it("opens on South Africa and still allows every country", () => {
    assert.equal(FLAGSHIP_COUNTRY, "South Africa");
    assert.equal(flagshipCountry(undefined), "South Africa");
    assert.equal(flagshipCountry("Kenya"), "Kenya");
    assert.equal(flagshipCountry("  Botswana "), "Botswana");
    assert.equal(flagshipCountry(""), "");
    assert.equal(flagshipCountry("all"), "");
    assert.equal(flagshipCountry(" All "), "");
    assert.equal(flagshipQuery(undefined), null);
    assert.equal(flagshipQuery("South Africa"), null);
    assert.equal(flagshipQuery(""), "all");
    assert.equal(flagshipQuery("all"), "all");
    assert.equal(flagshipQuery("Kenya"), "Kenya");
  });
});
