import { describe, expect, it } from "vitest";
import { countryOptions, sortCountries } from "./countries";

describe("country order", () => {
  it("puts South Africa, then SADC, then the rest of Africa, then other regions", () => {
    expect(sortCountries(["France", "Nigeria", "Botswana", "South Africa", "Germany", "Zambia"])).toEqual([
      "South Africa",
      "Botswana",
      "Zambia",
      "Nigeria",
      "France",
      "Germany",
    ]);
  });

  it("offers South Africa even when the catalogue has none", () => {
    expect(countryOptions(["Germany", "France"])[0]).toBe("South Africa");
  });
});
