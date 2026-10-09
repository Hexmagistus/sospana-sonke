/** Wording and rule for the "Not counted yet" vacancy label.

"Not counted yet" is not a vacancy count. It means Sospana could not read the
employer's vacancies, so clients must check the employer directly. The same
sentences are used on the badge tooltip, the list notice, and the Terms and
Privacy pages so the message does not drift.
*/

import type { Company } from "./types.js";

export const NOT_COUNTED_LABEL = "Not counted yet";

/** Always-visible short note beside the badge. */
export const NOT_COUNTED_INLINE = "That is not “no jobs”. Check their site.";

/** Tooltip on the badge. */
export const NOT_COUNTED_TOOLTIP =
  "This does not mean the employer has no vacancies. Their website or hiring system blocks " +
  "automated reading (or we cannot read it yet), so Sospana cannot count their jobs. " +
  "Open their careers link and check with the employer directly.";

export const NOT_COUNTED_NOTICE_TITLE = "“Not counted yet” does not mean “no vacancies”";

/** Full wording for the notice above a list. */
export const NOT_COUNTED_NOTICE_BODY =
  "Some employers' websites or hiring systems block automated reading, or we cannot read them yet, " +
  "so Sospana cannot count their jobs. An employer marked “Not counted yet” may well have openings. " +
  "Open the employer's careers link and check that employer directly, and keep checking such " +
  "employers yourself from time to time.";

/** Public careers feeds the scanner has a strategy for. JavaScript-only boards are not listed. */
export const READABLE_CAREERS_FEEDS =
  "Greenhouse, Lever, SmartRecruiters, Workable, Recruitee, Workday (its public jobs feed), " +
  "Oracle Candidate Experience, Breezy, Pinpoint, CareerInHR, Cornerstone, MCI, PeopleSoft, simplify.hr, and iCIMS";

export const READABLE_CAREERS_NOTE =
  "Open roles can be counted when the careers page is ordinary HTML we can read, or one of these public feeds: " +
  READABLE_CAREERS_FEEDS +
  ". A board we cannot read stays “Not counted yet”. That is not a count of zero.";

/** A vacancy count exists (a real zero included) or vacancies are held. */
export function hasCountedResult(company: Pick<Company, "open_vacancies" | "open_vacancies_known">): boolean {
  return company.open_vacancies_known === true || (company.open_vacancies ?? 0) > 0;
}

/** Same rule the card uses: a careers link exists and no count is known.
 * A known count (including a real zero) or any held vacancy is not "not counted". */
export function isNotCounted(
  company: Pick<Company, "careers_url" | "open_vacancies" | "open_vacancies_known">,
): boolean {
  if (!company.careers_url) return false;
  return !hasCountedResult(company);
}

export function anyNotCounted(
  companies: ReadonlyArray<Pick<Company, "careers_url" | "open_vacancies" | "open_vacancies_known">>,
): boolean {
  return companies.some(isNotCounted);
}
