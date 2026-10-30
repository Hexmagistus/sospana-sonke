/** Recognise common recruitment platforms from a careers URL. Notes stay generic on purpose:
 * menus differ per employer, so we never claim exact menu paths. */
export type Portal = { name: string; notes: string[] };

const RULES: { test: RegExp; portal: Portal }[] = [
  { test: /successfactors\.(com|eu)|jobs\.sap\.com|career\d*\.sapsf/i, portal: { name: "SAP SuccessFactors", notes: [
    "Many SuccessFactors career sites let you create a candidate profile and save a search as a job alert.",
    "Alerts are usually tied to a saved search, so search for the role or location you want first, then look for an option to save it or get emails.",
  ] } },
  { test: /myworkdayjobs\.com|workday\.com/i, portal: { name: "Workday", notes: [
    "Workday career sites usually offer a job alert option on the search results page and a candidate account for applications.",
    "Accounts are separate per employer: an account with one company's Workday site does not work on another's.",
  ] } },
  { test: /taleo\.net/i, portal: { name: "Oracle Taleo", notes: [
    "Taleo sites usually need a candidate profile before you can save job searches or subscribe to alerts.",
  ] } },
  { test: /oraclecloud\.com|\/hcmUI\/CandidateExperience/i, portal: { name: "Oracle Recruiting Cloud", notes: [
    "Oracle Candidate Experience sites often let you join a talent community or set job alerts with your email address.",
  ] } },
  { test: /OA_HTML|irecruit|\birec\./i, portal: { name: "Oracle iRecruitment", notes: [
    "iRecruitment sites use a registered candidate account; some offer saved searches that can email you new matches.",
    "Some work best in Chrome or Firefox.",
  ] } },
  { test: /\.ci\.hr/i, portal: { name: "CareerInHR (ci.hr)", notes: [
    "CareerInHR sites ask you to register a profile (often with a CV upload) before applying.",
  ] } },
  { test: /csod\.com|cornerstoneondemand/i, portal: { name: "Cornerstone (CSOD)", notes: [
    "Cornerstone career sites usually ask you to create a candidate account; some offer job alerts tied to a search.",
  ] } },
  { test: /erecruit\.co/i, portal: { name: "Graylink eRecruit (erecruit.co)", notes: [
    "These sites use a Sign Up / Log In candidate profile; complete the profile before applying.",
  ] } },
  { test: /pageuppeople\.com|pageup/i, portal: { name: "PageUp", notes: [
    "PageUp sites often offer a job alert option where you choose job categories and locations.",
  ] } },
  { test: /mcidirecthire\.com/i, portal: { name: "MCI Direct Hire", notes: [
    "Direct Hire sites use a Register / Log In candidate account and may let you upload your CV to their database.",
  ] } },
  { test: /smartrecruiters\.com/i, portal: { name: "SmartRecruiters", notes: [
    "SmartRecruiters sites often let you follow a company or join its talent community for updates.",
  ] } },
  { test: /greenhouse\.io|lever\.co|workable\.com/i, portal: { name: "Hosted job board", notes: [
    "This kind of job board often has no candidate account; check the page regularly or follow the employer on its official channels.",
  ] } },
];

export function detectPortal(url: string): Portal | null {
  for (const r of RULES) if (r.test.test(url)) return r.portal;
  return null;
}
