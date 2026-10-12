/** Public employer pages. Only rows with a careers link are addressable. */

import { canonicalType } from "./explorer/categoryGroups";
import { linkScope } from "./linkScope";

export type PublicEmployerSummary = {
  id: string;
  company_name: string;
  country: string;
  source_type: string;
};

export type PublicEmployerRole = {
  id: string;
  company_id: string;
  title: string;
  location: string | null;
  country: string | null;
  company_country: string;
  application_url: string | null;
  first_seen_at: string;
  last_seen_at: string;
  closing_date: string | null;
};

export type PublicEmployer = {
  id: string;
  company_name: string;
  country: string;
  source_type: string;
  careers_url: string;
  careers_scope: string | null;
  last_checked: string | null;
  url_looks_like_careers: boolean | null;
  open_role_count: number;
  roles: PublicEmployerRole[];
};

const CATEGORY_LABEL: Record<string, string> = {
  SOE: "State-owned",
  MUNI: "Municipality",
  DEPT: "Government department",
  PRIVATE: "Private company",
  NGO: "NGO",
  UNI: "University",
  COLLEGE: "College",
  HOSPITAL: "Hospital",
  SETA: "SETA",
  SPORT: "Sports association",
  FED: "Federation",
  MUSIC: "Music industry",
  JSE: "Listed company",
};

export function employerPath(id: string): string {
  return `/employers/${encodeURIComponent(id)}`;
}

export function categoryLabel(sourceType: string | null | undefined): string {
  const code = canonicalType(sourceType);
  if (!code) return "Employer";
  return CATEGORY_LABEL[code] ?? code;
}

/** What the stored row says. A missing marker is not called in-country. */
export function storedScopeText(scope: string | null | undefined): string {
  if (scope === "global") {
    return "The directory marks this as the employer's global careers board. The link is not filtered to one country.";
  }
  return "This row is not marked as a global board.";
}

export function urlScopeText(careersUrl: string): { label: string; detail: string } {
  const scope = linkScope(careersUrl);
  return { label: scope.label, detail: scope.detail };
}

export function checkedText(
  lastChecked: string | null | undefined,
  looksLikeCareers: boolean | null | undefined,
): string {
  const when = lastChecked ? lastChecked.slice(0, 10) : null;
  if (looksLikeCareers === true && when) return `URL check on ${when} recorded this as a careers page.`;
  if (looksLikeCareers === false && when) return `URL check on ${when} did not record this as a careers page.`;
  if (when) return `Last checked ${when}.`;
  return "No URL check recorded yet.";
}
