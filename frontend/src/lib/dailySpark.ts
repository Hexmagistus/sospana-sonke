// Daily Spark: which joke and wisdom belong to which day, and how to share them.
// Pure functions (no React, no network, no clock except where `now` is passed in) so the
// same date always yields the same spark for everyone and the rules can be unit-tested.
//
// "Today" is the Africa/Johannesburg calendar date. South African Standard Time is
// UTC+2 all year (no daylight saving), so a fixed offset is exact and needs no Intl data.

import { JOKES, WISDOM, type Joke, type Wisdom } from "./dailySparkData";

export interface Spark {
  date: string; // YYYY-MM-DD, SAST
  joke: Joke;
  wisdom: Wisdom;
}

const SAST_OFFSET_MS = 2 * 60 * 60 * 1000;
const DAY_MS = 24 * 60 * 60 * 1000;

/** The SAST calendar date (YYYY-MM-DD) for an instant. */
export function sastDateString(now: Date = new Date()): string {
  return new Date(now.getTime() + SAST_OFFSET_MS).toISOString().slice(0, 10);
}

/** Whole days since 1970-01-01 for a YYYY-MM-DD string (timezone-free). */
export function dayNumber(date: string): number {
  const [y, m, d] = date.split("-").map(Number);
  return Math.floor(Date.UTC(y, m - 1, d) / DAY_MS);
}

export function addDays(date: string, days: number): string {
  return new Date((dayNumber(date) + days) * DAY_MS).toISOString().slice(0, 10);
}

/** Small, stable PRNG (mulberry32) so the shuffled order is identical on every device. */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** A fixed shuffle of 0..n-1: every item appears exactly once per cycle, in a varied order. */
export function shuffledOrder(n: number, seed: number): number[] {
  const order = Array.from({ length: n }, (_, i) => i);
  const rand = mulberry32(seed);
  for (let i = n - 1; i > 0; i--) {
    const k = Math.floor(rand() * (i + 1));
    [order[i], order[k]] = [order[k], order[i]];
  }
  return order;
}

const JOKE_SEED = 0x5053a1;
const WISDOM_SEED = 0x57d0e5;
let jokeOrder: number[] | null = null;
let wisdomOrder: number[] | null = null;

function positive(n: number, mod: number): number {
  return ((n % mod) + mod) % mod;
}

/** The joke and wisdom for a date. Same date, same answer, on any device. */
export function pickSpark(date: string): Spark {
  jokeOrder ??= shuffledOrder(JOKES.length, JOKE_SEED);
  wisdomOrder ??= shuffledOrder(WISDOM.length, WISDOM_SEED);
  const day = dayNumber(date);
  return {
    date,
    joke: JOKES[jokeOrder[positive(day, JOKES.length)]],
    wisdom: WISDOM[wisdomOrder[positive(day, WISDOM.length)]],
  };
}

/** How many days pass before any joke or wisdom can repeat. */
export function noRepeatDays(): number {
  return Math.min(JOKES.length, WISDOM.length);
}

/** "Nelson Mandela, Long Walk to Freedom (1994)" or "African proverb (Swahili)". */
export function attribution(w: Wisdom): string {
  if (w.kind === "quote") return [w.author, w.source].filter(Boolean).join(", ");
  return w.origin ? `African proverb (${w.origin})` : "African proverb";
}

const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

/** Friendly long date: "Saturday 3 October 2026". Hand-rolled so it never depends on ICU data. */
export function prettyDate(date: string): string {
  const d = new Date(dayNumber(date) * DAY_MS);
  return `${WEEKDAYS[d.getUTCDay()]} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

/** Plain text that is nice to paste into WhatsApp, email or a notes app. */
export function shareText(spark: Spark, url?: string): string {
  const { joke, wisdom } = spark;
  const parts = [
    `Daily Spark · ${prettyDate(spark.date)}`,
    `Joke: ${joke.text}`,
    wisdom.native
      ? `Wisdom: “${wisdom.native}”\n“${wisdom.text}” (${attribution(wisdom)})`
      : `Wisdom: “${wisdom.text}” (${attribution(wisdom)})`,
  ];
  if (url) parts.push(url);
  return parts.join("\n\n");
}
