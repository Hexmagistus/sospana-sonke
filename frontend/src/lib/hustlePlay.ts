/**
 * Gauteng Hustle Run on Google Play (closed test).
 *
 * The game is listed in Play Console as "Bond Village Hustle"; Android package id
 * `com.bondvillage.hustlerun`. Only Google accounts on the closed-test tester list
 * can install it, and each tester must open the opt-in link once before the store
 * link works. Override either URL with NEXT_PUBLIC_HUSTLE_PLAY_URL /
 * NEXT_PUBLIC_HUSTLE_TESTING_URL on Vercel (e.g. when the game goes to open testing
 * or production) without a code change.
 */
export const HUSTLE_PACKAGE_ID = "com.bondvillage.hustlerun";
export const HUSTLE_PLAY_NAME = "Bond Village Hustle";

export const HUSTLE_PLAY_URL =
  process.env.NEXT_PUBLIC_HUSTLE_PLAY_URL || `https://play.google.com/store/apps/details?id=${HUSTLE_PACKAGE_ID}`;
export const HUSTLE_TESTING_URL =
  process.env.NEXT_PUBLIC_HUSTLE_TESTING_URL || `https://play.google.com/apps/testing/${HUSTLE_PACKAGE_ID}`;

/** Same shape the API's email check accepts (app/api/routes_game.py). */
export function isValidEmail(raw: string): boolean {
  const email = raw.trim();
  if (email.length < 6 || email.length > 254 || email.includes("..")) return false;
  return /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$/.test(email);
}
