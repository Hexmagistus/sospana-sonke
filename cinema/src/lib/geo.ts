import type { StreamSource } from "./types";

export function playbackAllowed(
  source: Pick<StreamSource, "licenceTerritories">,
  country: string | null,
): { allowed: boolean; reason: string } {
  const territories = source.licenceTerritories.map((item) => item.trim()).filter(Boolean);
  if (territories.length === 0 || territories.some((item) => item.toUpperCase() === "WORLD")) {
    return {
      allowed: true,
      reason: "The source record marks this title as worldwide. Copyright rules can still differ by country.",
    };
  }
  if (!country) {
    return {
      allowed: false,
      reason: `This title is limited to ${territories.join(", ")}. Choose where you are watching before it plays.`,
    };
  }
  const allowed = territories.some((item) => item.toLowerCase() === country.toLowerCase());
  if (!allowed) {
    return {
      allowed: false,
      reason: `The source record limits this title to ${territories.join(", ")}. It is not offered for ${country}.`,
    };
  }
  return { allowed: true, reason: `The source record includes ${country}.` };
}
