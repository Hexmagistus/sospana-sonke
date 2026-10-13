/** What a stored careers URL says about country scope.

The badge reads the address only. It does not claim the open roles are in
that country, and it does not call an unfiltered board "global".
*/

export type LinkScopeKind = "none" | "country" | "unfiltered" | "own" | "board";

export type LinkScope = {
  kind: LinkScopeKind;
  label: string;
  detail: string;
};

/** Applicant systems whose public board is not, by itself, limited to one country. */
const ATS_HOSTS = [
  "myworkdayjobs.com",
  "myworkdaysite.com",
  "workday.com",
  "greenhouse.io",
  "lever.co",
  "smartrecruiters.com",
  "workable.com",
  "ashbyhq.com",
  "recruitee.com",
  "teamtailor.com",
  "personio.com",
  "personio.de",
  "softgarden.io",
  "icims.com",
  "oraclecloud.com",
  "successfactors.com",
  "sapsf.com",
  "taleo.net",
  "breezy.hr",
  "pinpointhq.com",
  "jobvite.com",
  "simplify.hr",
  "ci.hr",
  "bamboohr.com",
  "csod.com",
  "eightfold.ai",
];

/** Hosts that are job boards, not the employer's own careers page. */
const BOARD_HOSTS = [
  "pnet.co.za",
  "careers24.com",
  "indeed.com",
  "linkedin.com",
  "facebook.com",
  "myjobmag.com",
  "myjobmag.co.za",
  "vacancymail.co.zw",
  "brightermonday.co.tz",
  "erecruit.co",
  "erecruit.co.za",
];

const COUNTRY_QUERY = new Set(["locationcountry", "location_country"]);

function hostOf(url: URL): string {
  return url.hostname.replace(/^www\./, "").toLowerCase();
}

function hostMatches(host: string, suffixes: readonly string[]): boolean {
  return suffixes.some((suffix) => host === suffix || host.endsWith(`.${suffix}`));
}

export function linkScope(raw: string | null | undefined): LinkScope {
  const value = (raw ?? "").trim();
  if (!value) {
    return {
      kind: "none",
      label: "No careers link",
      detail: "We do not have a careers page for this employer yet.",
    };
  }
  let url: URL;
  try {
    url = new URL(value.startsWith("http") ? value : `https://${value}`);
  } catch {
    return {
      kind: "none",
      label: "No careers link",
      detail: "The stored address is not a link we can read.",
    };
  }

  for (const [key, param] of url.searchParams) {
    if (COUNTRY_QUERY.has(key.toLowerCase()) && param.trim()) {
      return {
        kind: "country",
        label: "Country filter",
        detail: "The link includes a country filter from the employer's board. Open it to see the roles that filter returns.",
      };
    }
  }

  const host = hostOf(url);
  if (hostMatches(host, BOARD_HOSTS)) {
    return {
      kind: "board",
      label: "Third-party board",
      detail: "This link is a job board, not a page on the employer's own site.",
    };
  }
  if (hostMatches(host, ATS_HOSTS)) {
    return {
      kind: "unfiltered",
      label: "No country filter",
      detail: "This is the employer's public board. The link is not limited to one country, so the list can include roles elsewhere.",
    };
  }
  return {
    kind: "own",
    label: "Employer's page",
    detail: "This link is on the employer's own site. The address does not say whether the list is limited to one country.",
  };
}
