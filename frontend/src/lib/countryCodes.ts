/** Country codes for the directory's country names.

The URL carries a short code (?country=ZA). Codes come from the flag emoji the
site already uses (a flag is two regional-indicator letters, which are the ISO
3166-1 alpha-2 code), plus the countries the flag table does not cover yet.
Nothing here calls a service.
*/

import { COUNTRY_FLAGS } from "./countryFlags";

/** Directory spellings the flag table does not have yet. ISO 3166-1 alpha-2.
These are not in the directory; they are listed so a new country lands in its region. */
const EXTRA_CODES: Record<string, string> = {
  "Bermuda": "BM", "Cuba": "CU", "Greenland": "GL", "Macau": "MO",
  "Monaco": "MC", "Myanmar": "MM", "North Korea": "KP", "North Macedonia": "MK",
  "Puerto Rico": "PR", "San Marino": "SM", "Syria": "SY", "Tajikistan": "TJ", "Turkmenistan": "TM",
};

/** Directory buckets that are not one country. Codes are longer than two letters on purpose. */
export const BUCKET_CODES: Record<string, string> = { "Africa": "AFRICA", "International": "INTL" };

const A = 0x1f1e6;

function flagToCode(flag: string): string | null {
  const points = Array.from(flag).map((ch) => ch.codePointAt(0) ?? 0);
  if (points.length !== 2 || points.some((p) => p < A || p > A + 25)) return null;
  return points.map((p) => String.fromCharCode(65 + p - A)).join("");
}

function codeToFlag(code: string): string {
  return Array.from(code).map((ch) => String.fromCodePoint(A + ch.charCodeAt(0) - 65)).join("");
}

/** Code for a directory country name, or null when we have none. */
export function countryCode(name: string): string | null {
  if (BUCKET_CODES[name]) return BUCKET_CODES[name];
  const flag = COUNTRY_FLAGS[name];
  return (flag && flagToCode(flag)) || EXTRA_CODES[name] || null;
}

/** Flag emoji for a directory name. Buckets and unknown names get a globe. */
export function countryFlag(name: string): string {
  if (name === "International") return "🌐";
  if (name === "Africa") return "🌍";
  const code = countryCode(name);
  if (code && code.length === 2) return codeToFlag(code);
  return "🌍";
}

/**
 * Turn the ?country= value into a directory name. Accepts a code (ZA, za) or a
 * full name (South Africa), because older links and the coverage map use names.
 * Returns null if it matches nothing in `names`, so a typo never selects a ghost.
 */
export function resolveCountryParam(raw: string | null | undefined, names: readonly string[]): string | null {
  const value = (raw ?? "").trim();
  if (!value) return null;
  const upper = value.toUpperCase();
  for (const name of names) {
    if (countryCode(name) === upper) return name;
  }
  const lower = value.toLowerCase();
  for (const name of names) {
    if (name.toLowerCase() === lower) return name;
  }
  return null;
}

/** Every spelling we can give a flag or code to, for reading ?country= before the API answers. */
export const KNOWN_COUNTRY_NAMES: readonly string[] = Array.from(
  new Set([...Object.keys(COUNTRY_FLAGS), ...Object.keys(EXTRA_CODES), ...Object.keys(BUCKET_CODES)]),
);
