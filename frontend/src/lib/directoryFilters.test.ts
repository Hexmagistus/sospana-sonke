import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  DEFAULT_DIRECTORY_COUNTRY,
  DIRECTORY_GUIDE_STEPS,
  countryAfterFilterChange,
  countryFromDirectoryLink,
  directoryListPath,
  directorySliceKey,
} from "./directoryFilters.js";

describe("directory country stays when the category changes", () => {
  it("keeps South Africa when a category is chosen", () => {
    assert.equal(countryAfterFilterChange("South Africa", "SOE"), "South Africa");
    assert.equal(countryAfterFilterChange("South Africa", "Hospital"), "South Africa");
    assert.equal(countryAfterFilterChange("Kenya", "University"), "Kenya");
  });

  it("keeps All countries if the user had already chosen that", () => {
    assert.equal(countryAfterFilterChange("", "SETA"), "");
  });

  it("gives All and Listed a country when none is selected", () => {
    assert.equal(countryAfterFilterChange("", "all"), DEFAULT_DIRECTORY_COUNTRY);
    assert.equal(countryAfterFilterChange("", "listed"), DEFAULT_DIRECTORY_COUNTRY);
    assert.equal(countryAfterFilterChange("Namibia", "all"), "Namibia");
  });

  it("does not let a category link clear the country", () => {
    assert.equal(countryFromDirectoryLink({
      current: "South Africa",
      urlCountry: null,
      storedCountry: null,
    }), "South Africa");
    assert.equal(countryFromDirectoryLink({
      current: "South Africa",
      urlCountry: null,
      storedCountry: "Botswana",
    }), "Botswana");
    assert.equal(countryFromDirectoryLink({
      current: "Botswana",
      urlCountry: "Kenya",
      storedCountry: "Botswana",
    }), "Kenya");
  });

  it("asks the API for the country and the category together", () => {
    const path = directoryListPath({ country: "South Africa", sourceType: "SOE" });
    const params = new URL(path, "http://localhost").searchParams;
    assert.equal(params.get("country"), "South Africa");
    assert.equal(params.get("source_type"), "SOE");
    assert.equal(
      directorySliceKey({ shortlistKey: null, sourceType: "SOE", country: "South Africa" }),
      "type:SOE:country:South Africa",
    );
    const worldwide = directoryListPath({ country: "", sourceType: "HOSPITAL" });
    assert.equal(new URL(worldwide, "http://localhost").searchParams.get("country"), null);
  });

  it("lists four how-to steps", () => {
    assert.equal(DIRECTORY_GUIDE_STEPS.length, 4);
    assert.match(DIRECTORY_GUIDE_STEPS[0], /country/i);
    assert.match(DIRECTORY_GUIDE_STEPS[1], /category/i);
    assert.match(DIRECTORY_GUIDE_STEPS[2], /careers/i);
    assert.match(DIRECTORY_GUIDE_STEPS[3], /CV/i);
  });
});
