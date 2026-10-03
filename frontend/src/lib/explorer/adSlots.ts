/** Advertiser spots on the explorer pages: slot keys, form rules, the honest note.
Pure functions, so the minimum-amount rule is tested without a browser. The server
enforces the same rules (backend/app/schemas/ad.py); this only gives quick feedback. */

export const SLOTS_PER_SIDE = 10;
export const MIN_USD_PER_DAY = 1;
export const MAX_USD_PER_DAY = 10000;
export const MAX_DAYS = 365;
export const AD_TEXT_MAX = 120;

export type Side = "L" | "R";
export type PublicAd = { slot_key: string; business_name: string; ad_text: string; website: string };

/** "L1".."L10" for the left column, "R1".."R10" for the right. */
export function slotKeys(side: Side): string[] {
  return Array.from({ length: SLOTS_PER_SIDE }, (_, i) => `${side}${i + 1}`);
}

export const MIN_NOTE =
  "Minimum $1/day is roughly what it costs to keep Sospana Sonke online and free for job seekers.";
export const NO_PAYMENT_NOTE =
  "Applying does not charge you. If your ad is approved, payment instructions follow by email.";

export type AdForm = {
  businessName: string;
  email: string;
  website: string;
  adText: string;
  amount: string;
  days: string;
};

export const EMPTY_FORM: AdForm = { businessName: "", email: "", website: "", adText: "", amount: "1", days: "7" };

export type AdErrors = Partial<Record<keyof AdForm, string>>;

/** Parse "1", "1.5", "2,50" to a number, or NaN when it is not a plain amount. */
export function parseAmount(raw: string): number {
  const t = raw.trim().replace(",", ".");
  if (!/^\d+(\.\d{1,2})?$/.test(t)) return NaN;
  return Number(t);
}

export function validateAdForm(f: AdForm): AdErrors {
  const e: AdErrors = {};
  if (f.businessName.trim().length < 2) e.businessName = "Enter your business name.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(f.email.trim())) e.email = "Enter a valid email address.";
  const site = f.website.trim();
  let host = "";
  try { host = new URL(/^https?:\/\//i.test(site) ? site : `https://${site}`).hostname; } catch { /* invalid */ }
  if (!site || !host.includes(".") || /\s/.test(site)) e.website = "Enter your website address, for example https://example.com";
  const text = f.adText.trim();
  if (text.length < 3) e.adText = "Write a short ad.";
  else if (text.length > AD_TEXT_MAX) e.adText = `Keep it to ${AD_TEXT_MAX} characters or fewer.`;
  const amount = parseAmount(f.amount);
  if (Number.isNaN(amount)) e.amount = "Enter an amount in US dollars, for example 1 or 2.50.";
  else if (amount < MIN_USD_PER_DAY) e.amount = `The minimum is $${MIN_USD_PER_DAY} per day.`;
  else if (amount > MAX_USD_PER_DAY) e.amount = "That amount is too large. Please contact us instead.";
  const days = Number(f.days);
  if (!Number.isInteger(days) || days < 1 || days > MAX_DAYS) e.days = `Enter a whole number of days from 1 to ${MAX_DAYS}.`;
  return e;
}

/** Total for the form, or null while the amount or days are not valid. */
export function totalUsd(f: AdForm): number | null {
  const a = parseAmount(f.amount);
  const d = Number(f.days);
  if (Number.isNaN(a) || a < MIN_USD_PER_DAY || !Number.isInteger(d) || d < 1) return null;
  return Math.round(a * d * 100) / 100;
}

/** Body for POST /ads/applications. Call only when validateAdForm returned no errors. */
export function toPayload(f: AdForm, slot: string | null) {
  return {
    business_name: f.businessName.trim(),
    contact_email: f.email.trim(),
    website: f.website.trim(),
    ad_text: f.adText.trim(),
    amount_usd_per_day: parseAmount(f.amount).toFixed(2),
    days: Number(f.days),
    requested_slot: slot,
  };
}

/** A web address is only linked when it is http or https. */
export function safeHref(url: string): string | null {
  try {
    const u = new URL(url);
    return u.protocol === "http:" || u.protocol === "https:" ? u.toString() : null;
  } catch { return null; }
}
