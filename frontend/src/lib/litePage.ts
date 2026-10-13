/** Text-only pages. No script, picture, or sound belongs in this HTML. */

import { flagshipCountry, flagshipQuery } from "./flagship";

export const LITE_LIMIT = 8;

export type LiteJob = {
  id: string;
  title: string;
  company_name: string;
  company_id?: string;
  company_country?: string;
  location?: string | null;
  closing_date?: string | null;
  last_seen_at?: string;
  application_url?: string | null;
  opportunity_type?: string | null;
};

export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** Connection Save-Data, the on-device data-saver switch, or a /lite path. */
export function blocksHeavyMedia(
  connectionSaveData: boolean,
  storedChoice: string | null,
  litePath: boolean,
): boolean {
  return litePath || connectionSaveData || storedChoice === "1";
}

/** Suggest the text site when the browser asks to save data, unless the reader chose the full site. */
export function shouldSuggestLite(saveDataHeader: string | null, siteCookie: string | undefined): boolean {
  if (siteCookie === "full") return false;
  return saveDataHeader === "on" || siteCookie === "lite";
}

/** Only a same-site path. A scheme or a protocol-relative URL stays on the home page. */
export function safeReturnPath(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\") || /[\r\n]/.test(value)) {
    return "/";
  }
  return value.slice(0, 200);
}

export function liteDocument(title: string, main: string): string {
  const safeTitle = escapeHtml(title);
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${safeTitle}</title>
<style>
body{font:16px/1.45 system-ui,sans-serif;margin:1rem;color:#0b1220;background:#fff}
a{color:#0f766e}
nav,form,p{margin:0 0 1rem}
input,button{font:inherit;min-height:2.75rem}
h1{font-size:1.4rem;line-height:1.2}
ul{padding-left:1.2rem}
</style>
</head>
<body>
<nav><a href="/lite">Search</a> · <a href="/lite/opportunities">Programmes</a> · <a href="/lite/choice?to=full&amp;next=/">Full site</a></nav>
${main}
</body>
</html>`;
}

export function liteQuery(params: { q?: string; country?: string; type?: string; offset?: string }): string {
  const search = new URLSearchParams();
  const q = (params.q || "").trim().slice(0, 80);
  if (q) search.set("q", q);
  const country = flagshipQuery(params.country);
  if (country) search.set("country", country);
  const type = (params.type || "").trim().slice(0, 32);
  if (type) search.set("type", type);
  const offset = Number(params.offset);
  if (Number.isInteger(offset) && offset > 0 && offset <= 500) search.set("offset", String(offset));
  const text = search.toString();
  return text ? `?${text}` : "";
}

function jobLine(job: LiteJob): string {
  const title = escapeHtml(job.title.slice(0, 140));
  const employer = job.company_id
    ? `<a href="/lite/employers/${encodeURIComponent(job.company_id)}">${escapeHtml(job.company_name.slice(0, 80))}</a>`
    : escapeHtml(job.company_name.slice(0, 80));
  const place = [job.location, job.company_country].filter(Boolean).slice(0, 2).join(", ");
  const closes = job.closing_date ? ` Closes ${escapeHtml(job.closing_date.slice(0, 10))}.` : "";
  return `<li><a href="/lite/jobs/${encodeURIComponent(job.id)}">${title}</a> — ${employer}${place ? ` (${escapeHtml(place.slice(0, 80))})` : ""}.${closes}</li>`;
}

export function liteSearchPage(input: {
  q: string;
  country: string | undefined;
  jobs: LiteJob[] | null;
  matched: number | null;
  offset: number;
}): string {
  const country = flagshipCountry(input.country);
  const q = input.q.slice(0, 80);
  let list = "<p>The role list could not be reached. No substitute list is shown.</p>";
  if (input.jobs && input.matched === 0) {
    list = "<p>No stored role matches. That does not mean the employer has nothing open.</p>";
  } else if (input.jobs) {
    const lines = input.jobs.slice(0, LITE_LIMIT).map(jobLine).join("");
    const from = input.offset + 1;
    const to = input.offset + input.jobs.length;
    list = `<p>Showing ${from}–${to} of ${input.matched} stored roles. ${escapeHtml(country || "All countries")}.</p><ul>${lines}</ul>`;
  }
  const nextOffset = input.offset + LITE_LIMIT;
  const prevOffset = Math.max(0, input.offset - LITE_LIMIT);
  const more = input.jobs && input.matched !== null && nextOffset < input.matched
    ? `<p><a href="/lite${liteQuery({ q, country: input.country, offset: String(nextOffset) })}">Next</a></p>`
    : "";
  const prev = input.offset > 0
    ? `<p><a href="/lite${liteQuery({ q, country: input.country, offset: String(prevOffset) })}">Previous</a></p>`
    : "";
  return liteDocument("Search stored roles", `
<h1>Search stored roles</h1>
<p>Text only. South Africa is the starting country. Clear the country box to search every country. You apply on the employer's own page.</p>
<form method="get" action="/lite">
<p><label>Keyword <input name="q" value="${escapeHtml(q)}" maxlength="80"></label></p>
<p><label>Country <input name="country" value="${escapeHtml(country)}" maxlength="80"></label></p>
<p><button type="submit">Search</button></p>
</form>
${list}
${prev}
${more}`);
}

export function liteProgrammesPage(input: {
  type: string;
  jobs: LiteJob[] | null;
  matched: number | null;
}): string {
  const types = [
    ["", "All"],
    ["learnership", "Learnerships"],
    ["bursary", "Bursaries"],
    ["internship", "Internships"],
    ["graduate_programme", "Graduate programmes"],
  ];
  const links = types.map(([value, label]) => {
    const href = `/lite/opportunities${liteQuery({ type: value, country: undefined })}`;
    return `<a href="${href}">${label}</a>`;
  }).join(" · ");
  let list = "<p>The programme list could not be reached.</p>";
  if (input.jobs && input.matched === 0) list = "<p>No stored programme matches.</p>";
  else if (input.jobs) {
    list = `<p>${input.matched} stored programmes. South Africa is listed first when no country is named.</p><ul>${input.jobs.slice(0, LITE_LIMIT).map(jobLine).join("")}</ul>`;
  }
  return liteDocument("Programmes", `<h1>Internships, learnerships, bursaries and graduate programmes</h1><p>${links}</p>${list}`);
}

export function liteEmployerPage(input: {
  id: string;
  name: string;
  country: string;
  careersUrl: string;
  openCount: number;
  roles: LiteJob[];
} | null): string {
  if (!input) {
    return liteDocument("Employer", "<h1>Employer</h1><p>This employer is not in the directory, or the directory did not answer. No name was invented.</p>");
  }
  const roles = input.roles.slice(0, LITE_LIMIT).map(jobLine).join("");
  return liteDocument(input.name, `
<h1>${escapeHtml(input.name.slice(0, 120))}</h1>
<p>${escapeHtml(input.country)}. Stored open roles: ${input.openCount}. Showing ${Math.min(input.roles.length, LITE_LIMIT)}.</p>
<p>Careers page: <a href="${escapeHtml(input.careersUrl)}">${escapeHtml(input.careersUrl.slice(0, 180))}</a></p>
<p><a href="/lite/choice?to=full&amp;next=${encodeURIComponent(`/employers/${input.id}`)}">Full page</a></p>
${roles ? `<ul>${roles}</ul>` : "<p>No open role is stored. That does not mean the careers page is empty.</p>"}`);
}

export function liteJobPage(job: LiteJob | null): string {
  if (!job) {
    return liteDocument("Role", "<h1>Role</h1><p>This stored role is not available. No substitute advert is shown.</p>");
  }
  const apply = job.application_url
    ? `<p>Apply on the source page: <a href="${escapeHtml(job.application_url)}">${escapeHtml(job.application_url.slice(0, 180))}</a></p>`
    : "<p>No application link was stored.</p>";
  const employer = job.company_id
    ? `<a href="/lite/employers/${encodeURIComponent(job.company_id)}">${escapeHtml(job.company_name)}</a>`
    : escapeHtml(job.company_name);
  return liteDocument(job.title, `
<h1>${escapeHtml(job.title.slice(0, 160))}</h1>
<p>${employer}${job.company_country ? ` · ${escapeHtml(job.company_country)}` : ""}</p>
<p>${job.location ? escapeHtml(job.location) + ". " : ""}${job.closing_date ? `Closes ${escapeHtml(job.closing_date.slice(0, 10))}.` : "No closing date was stored."}</p>
${apply}
<p>Sospana Sonke does not send the application.</p>
<p><a href="/lite/choice?to=full&amp;next=${encodeURIComponent(`/jobs/${job.id}`)}">Full page</a></p>`);
}
