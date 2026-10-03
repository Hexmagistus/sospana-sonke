/** The three client preferences, and how each one reads on screen. */

export type YesNoState = "not_chosen" | "yes" | "no";

/** Keep in step with POST_TYPES in backend/app/models/user.py. */
export const POST_TYPES: { value: string; label: string }[] = [
  { value: "any", label: "Any kind of post" },
  { value: "permanent", label: "Permanent" },
  { value: "contract", label: "Contract or fixed term" },
  { value: "part_time", label: "Part time" },
  { value: "internship", label: "Internship or work experience" },
  { value: "learnership", label: "Learnership or apprenticeship" },
  { value: "graduate", label: "Graduate programme" },
  { value: "none", label: "Don't consider me for posts right now" },
];

export function postTypeLabel(value: string | null | undefined): string {
  if (!value) return "Not chosen";
  return POST_TYPES.find((p) => p.value === value)?.label ?? "Not chosen";
}

export function yesNoLabel(state: string | undefined): string {
  if (state === "yes") return "Yes";
  if (state === "no") return "No";
  return "Not chosen";
}

export type PrefSummary = {
  tagging_state?: string;
  preferred_post_state?: string;
  alerts_state?: string;
};

/** How many of the three are still "not chosen yet". */
export function unchosenCount(u: PrefSummary | null | undefined): number {
  if (!u) return 0;
  return [u.tagging_state, u.preferred_post_state, u.alerts_state]
    .filter((s) => !s || s === "not_chosen").length;
}

/** The banner shows while any preference is unchosen. There is no dismiss. */
export function needsBanner(u: (PrefSummary & { role?: string; show_consent_banner?: boolean }) | null | undefined): boolean {
  if (!u) return false;
  if (typeof u.show_consent_banner === "boolean") return u.show_consent_banner;
  return u.role !== "admin" && unchosenCount(u) > 0;
}
