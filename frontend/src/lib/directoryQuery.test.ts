import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  employerSuggestions,
  matchesBoardFilter,
  matchesNameQuery,
  matchesScopeFilter,
  refineIsNarrowed,
} from "./directoryQuery.js";

const rows = [
  { company_name: "Eskom", jse_code: null, careers_url: "https://www.eskom.co.za/careers", open_vacancies: 3 },
  { company_name: "Côte Mines", jse_code: "CTM", careers_url: "https://boards.greenhouse.io/cote", open_vacancies: 0 },
  { company_name: "Aviva", jse_code: null, careers_url: "https://aviva.wd1.myworkdayjobs.com/External?Location_Country=abc", open_vacancies: 8 },
  { company_name: "Blank Bank", jse_code: null, careers_url: "", open_vacancies: 0 },
];

describe("directory name search", () => {
  it("matches a name or a listing code, ignoring accents", () => {
    assert.equal(matchesNameQuery(rows[1], "cote"), true);
    assert.equal(matchesNameQuery(rows[1], "ctm"), true);
    assert.equal(matchesNameQuery(rows[0], "eskom"), true);
    assert.equal(matchesNameQuery(rows[0], "aviva"), false);
  });

  it("puts names that start with the query first", () => {
    const named = [
      { company_name: "FirstRand" },
      { company_name: "Rand Merchant Bank" },
      { company_name: "Rand Water" },
    ];
    assert.deepEqual(
      employerSuggestions(named, "rand", 3),
      ["Rand Merchant Bank", "Rand Water", "FirstRand"],
    );
  });
});

describe("directory extra filters", () => {
  it("keeps open roles only when the stored count is above zero", () => {
    assert.equal(matchesBoardFilter(rows[0], "open"), true);
    assert.equal(matchesBoardFilter(rows[1], "open"), false);
    assert.equal(matchesBoardFilter(rows[3], "linked"), false);
    assert.equal(matchesBoardFilter(rows[3], "blank"), true);
  });

  it("filters by the link-scope kind", () => {
    assert.equal(matchesScopeFilter(rows[2], "country"), true);
    assert.equal(matchesScopeFilter(rows[1], "unfiltered"), true);
    assert.equal(matchesScopeFilter(rows[0], "own"), true);
    assert.equal(matchesScopeFilter(rows[3], "own"), false);
  });

  it("knows when the extra filters are still the whole list", () => {
    assert.equal(refineIsNarrowed("", "all", "all"), false);
    assert.equal(refineIsNarrowed("es", "all", "all"), true);
    assert.equal(refineIsNarrowed("", "open", "all"), true);
    assert.equal(refineIsNarrowed("", "all", "country"), true);
  });
});
