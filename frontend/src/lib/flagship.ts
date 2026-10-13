/** Featured country for search, jobs, and programmes. */
export const FLAGSHIP_COUNTRY = "South Africa";

/**
 * Country sent to the public jobs API.
 * An absent value is South Africa. "all" or a blank value means every country.
 */
export function flagshipCountry(value: string | undefined): string {
  if (value === undefined) return FLAGSHIP_COUNTRY;
  const trimmed = value.trim();
  if (!trimmed || trimmed.toLowerCase() === "all") return "";
  return trimmed.slice(0, 80);
}

/**
 * Country kept on a page link.
 * The featured country is omitted so the default URL stays short.
 * "all" is kept so a later page does not snap back to South Africa.
 */
export function flagshipQuery(value: string | undefined): string | null {
  if (value === undefined) return null;
  const trimmed = value.trim();
  if (!trimmed || trimmed.toLowerCase() === "all") return "all";
  if (trimmed === FLAGSHIP_COUNTRY) return null;
  return trimmed.slice(0, 80);
}
