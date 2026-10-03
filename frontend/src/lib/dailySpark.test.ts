import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  addDays, attribution, dayNumber, noRepeatDays, pickSpark, prettyDate, sastDateString,
  shareText, shuffledOrder,
} from "./dailySpark";
import { JOKES, REGION_ORDER, WISDOM } from "./dailySparkData";

// Every named person below was checked against a well-documented source. Adding a new
// name here is a deliberate act: confirm the attribution first, then add it.
const APPROVED_AUTHORS = new Set([
  "Nelson Mandela", "Desmond Tutu", "Wangari Maathai", "Chinua Achebe", "Seneca",
  "Marcus Aurelius", "Confucius", "Lao Tzu", "Epictetus", "Socrates", "Plato", "Terence",
  "Virgil", "Cicero", "Horace", "Aesop", "Benjamin Franklin", "William Shakespeare",
  "Ecclesiastes", "Proverbs", "Samuel Johnson", "Henry David Thoreau", "Ralph Waldo Emerson",
]);

describe("content", () => {
  it("ships at least 120 jokes and 120 wisdoms", () => {
    assert.ok(JOKES.length >= 120, `jokes: ${JOKES.length}`);
    assert.ok(WISDOM.length >= 120, `wisdom: ${WISDOM.length}`);
  });

  it("has unique ids and no duplicate texts", () => {
    for (const list of [JOKES, WISDOM]) {
      assert.equal(new Set(list.map((x) => x.id)).size, list.length);
    }
    assert.equal(new Set(JOKES.map((x) => x.text)).size, JOKES.length);
    const wisdomKeys = WISDOM.map((x) => `${x.text}|${x.origin ?? ""}|${x.author ?? ""}`);
    assert.equal(new Set(wisdomKeys).size, WISDOM.length);
  });

  it("keeps lengths readable on a phone", () => {
    for (const x of JOKES) assert.ok(x.text.length >= 25 && x.text.length <= 260, x.id);
    for (const x of WISDOM) assert.ok(x.text.length >= 10 && x.text.length <= 330, x.id);
  });

  it("attributes quotes only to approved, sourced authors and never gives proverbs an author", () => {
    for (const x of WISDOM) {
      if (x.kind === "quote") {
        assert.ok(x.author && APPROVED_AUTHORS.has(x.author), `${x.id}: ${x.author}`);
        assert.ok(x.source && x.source.length > 3, `${x.id} needs a source`);
      } else {
        assert.equal(x.author, undefined, `${x.id} is a proverb but has an author`);
        assert.match(attribution(x), /^African proverb/);
      }
    }
  });

  it("lists wisdom South Africa, then SADC, then Africa, then everywhere else", () => {
    const ranks = WISDOM.map((x) => REGION_ORDER[x.region]);
    assert.deepEqual(ranks, [...ranks].sort((a, b) => a - b));
    assert.ok(ranks.includes(0) && ranks.includes(1) && ranks.includes(2) && ranks.includes(3));
  });

  it("includes the Ubuntu proverb as an African proverb", () => {
    const u = WISDOM.find((x) => x.native === "Umuntu ngumuntu ngabantu.");
    assert.ok(u);
    assert.equal(u.kind, "proverb");
    assert.equal(u.text, "A person is a person through other people.");
  });

  it("stays clean: no coarse language or guilt phrasing", () => {
    const banned = /\b(damn|hell|shit|fuck|crap|bastard|idiot|stupid|lazy|loser|sexy|drunk)\b/i;
    for (const x of [...JOKES, ...WISDOM]) assert.doesNotMatch(x.text, banned, x.id);
  });
});

describe("dates", () => {
  it("rolls over at midnight South African time (22:00 UTC)", () => {
    assert.equal(sastDateString(new Date("2026-10-03T21:59:59Z")), "2026-10-03");
    assert.equal(sastDateString(new Date("2026-10-03T22:00:00Z")), "2026-10-04");
    assert.equal(sastDateString(new Date("2026-01-01T00:30:00Z")), "2026-01-01"); // no DST
    assert.equal(sastDateString(new Date("2026-12-31T22:30:00Z")), "2027-01-01");
  });

  it("does date arithmetic across months and leap years", () => {
    assert.equal(addDays("2026-03-01", -1), "2026-02-28");
    assert.equal(addDays("2028-03-01", -1), "2028-02-29");
    assert.equal(addDays("2026-12-31", 1), "2027-01-01");
    assert.equal(dayNumber("1970-01-02"), 1);
  });

  it("formats a friendly date", () => {
    assert.equal(prettyDate("2026-10-03"), "Saturday 3 October 2026");
    assert.equal(prettyDate("2028-02-29"), "Tuesday 29 February 2028");
  });
});

describe("daily pick", () => {
  it("is deterministic: same date, same spark", () => {
    const a = pickSpark("2026-10-03");
    const b = pickSpark("2026-10-03");
    assert.equal(a.joke.id, b.joke.id);
    assert.equal(a.wisdom.id, b.wisdom.id);
  });

  it("never repeats a joke or wisdom within the no-repeat window", () => {
    const days = noRepeatDays();
    assert.ok(days >= 120);
    const jokes = new Set<string>();
    const wisdoms = new Set<string>();
    for (let i = 0; i < days; i++) {
      const s = pickSpark(addDays("2026-10-03", i));
      jokes.add(s.joke.id);
      wisdoms.add(s.wisdom.id);
    }
    assert.equal(jokes.size, days);
    assert.equal(wisdoms.size, days);
  });

  it("covers every item over a full cycle and yesterday differs from today", () => {
    const seenJ = new Set<string>();
    const seenW = new Set<string>();
    for (let i = 0; i < Math.max(JOKES.length, WISDOM.length); i++) {
      const s = pickSpark(addDays("2026-01-01", i));
      seenJ.add(s.joke.id);
      seenW.add(s.wisdom.id);
    }
    assert.equal(seenJ.size, JOKES.length);
    assert.equal(seenW.size, WISDOM.length);
    assert.notEqual(pickSpark("2026-10-03").joke.id, pickSpark(addDays("2026-10-03", -1)).joke.id);
  });

  it("shuffles into a true permutation, identically every time", () => {
    const a = shuffledOrder(50, 7);
    assert.deepEqual([...a].sort((x, y) => x - y), Array.from({ length: 50 }, (_, i) => i));
    assert.deepEqual(a, shuffledOrder(50, 7));
  });
});

describe("share text", () => {
  it("contains the joke, the wisdom and a correct attribution", () => {
    const s = pickSpark("2026-10-03");
    const t = shareText(s, "https://example.test");
    assert.ok(t.includes(s.joke.text));
    assert.ok(t.includes(s.wisdom.text));
    assert.ok(t.includes(attribution(s.wisdom)));
    assert.ok(t.endsWith("https://example.test"));
  });

  it("labels proverbs as African proverbs", () => {
    const proverb = WISDOM.find((x) => x.kind === "proverb" && !x.origin)!;
    const t = shareText({ date: "2026-10-03", joke: JOKES[0], wisdom: proverb });
    assert.ok(t.includes("(African proverb)"));
  });
});
