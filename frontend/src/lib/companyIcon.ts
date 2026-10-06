/** URL of the icon OUR API stores for a company, or null when there is none.

The directory only asks for an icon when the list response says the API has
one (has_icon). That skips a request per card for the ~75% of employers with
no icon. icon_version goes in the URL (?v=): it changes when the icon job
stores a new icon, so the API can mark the response immutable for a year and
the browser never asks again for that URL. */
export function companyIconSrc(
  apiBase: string,
  id: string | null | undefined,
  hasIcon: boolean | null | undefined,
  iconVersion?: number | null,
): string | null {
  if (!id || !hasIcon) return null;
  const v =
    typeof iconVersion === "number" && Number.isFinite(iconVersion) && iconVersion >= 0
      ? `?v=${Math.trunc(iconVersion)}`
      : "";
  return `${apiBase}/companies/${encodeURIComponent(id)}/icon${v}`;
}
