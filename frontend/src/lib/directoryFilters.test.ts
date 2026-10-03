import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  DEFAULT_DIRECTORY_COUNTRY,
  DIRECTORY_GUIDE_STEPS,
  compareCountries,
  countryAfterFilterChange,
  categoryChipCount,
  categoryChipLinked,
  countryFromDirectoryLink,
  directoryListPath,
  directorySliceKey,
  sortCountries,
} from "./directoryFilters.js";

// The CI step runs this one file. These register the split-view tests with it.
import "./countryExplorer.test.js";
import "./explorer/CountrySidebar.test.js";
import "./explorer/sidebarWidth.test.js";
import "./explorer/ExplorerControls.test.js";

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

  it("orders South Africa, then SADC, then Africa, then other regions", () => {
    assert.deepEqual(
      sortCountries(["Kenya", "Australia", "Botswana", "South Africa", "Nigeria", "Zimbabwe", "France"]),
      ["South Africa", "Botswana", "Zimbabwe", "Kenya", "Nigeria", "Australia", "France"],
    );
    assert.ok(compareCountries("Angola", "Botswana") < 0);
    assert.ok(compareCountries("Zimbabwe", "Nigeria") < 0);
    assert.ok(compareCountries("Egypt", "Brazil") < 0);
    assert.ok(compareCountries("United Kingdom", "Zambia") > 0);
  });

  it("lists four how-to steps", () => {
    assert.equal(DIRECTORY_GUIDE_STEPS.length, 4);
    assert.match(DIRECTORY_GUIDE_STEPS[0], /country/i);
    assert.match(DIRECTORY_GUIDE_STEPS[1], /category/i);
    assert.match(DIRECTORY_GUIDE_STEPS[2], /careers/i);
    assert.match(DIRECTORY_GUIDE_STEPS[3], /CV/i);
  });
});

describe("category chip counts follow the selected country", () => {
  const facets = {
    type_counts: { UNI: 561, COLLEGE: 354 },
    country_type_counts: { "South Africa": { UNI: 26, COLLEGE: 107 }, Kenya: { UNI: 45 } },
    country_type_with_links: { "South Africa": { UNI: 26, COLLEGE: 59 } },
  };

  it("uses the country's own count when a country is chosen", () => {
    assert.equal(categoryChipCount(facets, "South Africa", "UNI"), 26);
    assert.equal(categoryChipCount(facets, "South Africa", "COLLEGE"), 107);
    assert.equal(categoryChipLinked(facets, "South Africa", "COLLEGE"), 59);
  });

  it("is zero, not the worldwide number, where the country has none", () => {
    assert.equal(categoryChipCount(facets, "Kenya", "COLLEGE"), 0);
    assert.equal(categoryChipCount(facets, "South Africa", "FED"), 0);
  });

  it("uses the worldwide total only for all countries", () => {
    assert.equal(categoryChipCount(facets, "", "UNI"), 561);
  });

  it("copes with an old API that has no per-country counts", () => {
    assert.equal(categoryChipCount({ type_counts: { UNI: 9 } }, "South Africa", "UNI"), 0);
    assert.equal(categoryChipCount(null, "", "UNI"), 0);
  });
});
