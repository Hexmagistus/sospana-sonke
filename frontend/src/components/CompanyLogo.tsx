"use client";

import { useMemo, useState } from "react";

// Careers links that sit on a third-party ATS / job board — their favicon is the
// platform's logo, not the employer's, so we never take the logo from these.
const ATS_DOMAINS = [
  // Global ATS platforms
  "myworkdayjobs.com", "workday.com", "myworkdaysite.com",
  "successfactors.com", "sapsf.com", "oraclecloud.com", "taleo.net",
  "greenhouse.io", "lever.co", "smartrecruiters.com", "workable.com",
  "erecruit.co", "erecruit.co.za", "mcidirecthire.com", "pnet.co.za", "careers24.com",
  "simplify.hr", "jobvite.com", "icims.com", "bamboohr.com", "breezy.hr",
  "recruitmentportal.co.za", "ci.hr", "placementpartner.co.za", "mnetjobs.com",
  "eightfold.ai", "pinpointhq.com", "csod.com", "trending-talent.com",
  "wamly.io", "hr.com", "jobartis.com", "emprego.co.mz",
  // Country/regional job boards — real employer-branded pages, but the favicon
  // is the board's, not the employer's.
  "vacancymail.co.zw", "jobwebzambia.com", "greatzambiajobs.com", "lesothoyp.com",
  "makeyourmove.co.tz", "myjob.mu", "jobsearchmalawi.com", "brightermonday.co.tz",
  // Social / directory sites that sometimes stand in for a careers page
  "linkedin.com", "facebook.com", "indeed.com", "za.indeed.com", "blogspot.com",
  // White-label recruitment SaaS / third-party job media that some employers
  // point their "careers" link at — favicon is the platform's, not theirs.
  "scubedonline.co.za", "skillsmapafrica.com", "applicantpro.com",
  "myjobmag.co.za", "myjobmag.com", "builtin.com",
];

const COMPANY_SUFFIXES = /\b(ltd|limited|pty|proprietary|holdings?|group|soc|inc|incorporated|corporation|corp|company|co|plc|rf|sa|the)\b/gi;

// The country-appropriate TLD(s) to try first when guessing a company's domain
// from its name — tried before the generic .com/.co.za fallback.
const COUNTRY_TLDS: Record<string, string[]> = {
  "South Africa": ["co.za"],
  "Zimbabwe": ["co.zw"],
  "Zambia": ["co.zm"],
  "Malawi": ["mw"],
  "Namibia": ["com.na"],
  "Botswana": ["co.bw"],
  "Eswatini": ["co.sz"],
  "Mozambique": ["co.mz"],
  "Tanzania": ["co.tz"],
  "Angola": ["co.ao", "ao"],
  "Lesotho": ["co.ls"],
  "Mauritius": ["mu"],
  "Madagascar": ["mg"],
  "DR Congo": ["cd"],
  "Seychelles": ["sc"],
  "Comoros": ["km"],
};

function domainFrom(url?: string | null): string | null {
  if (!url) return null;
  try {
    const u = new URL(url.startsWith("http") ? url : `https://${url}`);
    return u.hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return null;
  }
}

function isATS(domain: string | null): boolean {
  return !!domain && ATS_DOMAINS.some((x) => domain === x || domain.endsWith(`.${x}`));
}

export function isAtsPortal(url?: string | null): boolean {
  return isATS(domainFrom(url));
}

function slugFromName(name: string): string {
  return name
    .toLowerCase()
    .replace(/\(.*?\)/g, " ")        // drop parentheticals e.g. "(RTMC)"
    .replace(/&/g, " and ")
    .replace(COMPANY_SUFFIXES, " ")
    .replace(/[^a-z0-9]+/g, "");
}

function initials(name: string): string {
  const parts = name.replace(/[^A-Za-z0-9 ]/g, "").trim().split(/\s+/);
  const two = ((parts[0]?.[0] || "") + (parts[1]?.[0] || "")).toUpperCase();
  return two || (name[0] || "?").toUpperCase();
}

export function CompanyLogo({
  name,
  website,
  careersUrl,
  country,
  gradient,
}: {
  name: string;
  website?: string | null;
  careersUrl?: string | null;
  country?: string | null;
  gradient: string;
}) {
  const sources = useMemo(() => {
    const siteDomain = domainFrom(website);
    const careersDomain = domainFrom(careersUrl);
    // Prefer a real, non-ATS domain we already know.
    const known = siteDomain || (careersDomain && !isATS(careersDomain) ? careersDomain : null);
    if (known) {
      return [`https://logo.clearbit.com/${known}`, `https://www.google.com/s2/favicons?domain=${known}&sz=128`];
    }
    // Otherwise guess the company's own domain from its name and only accept a
    // genuine logo (Clearbit 404s for unknown domains → we fall back to initials,
    // so a wrong brand is never shown). Try the country's own TLD(s) first
    // (most African corporate sites live there, not .com), then .com/.co.za.
    const slug = slugFromName(name);
    if (slug.length >= 3) {
      const tlds = [...(country ? COUNTRY_TLDS[country] || [] : []), "com", "co.za"];
      const uniqueTlds = Array.from(new Set(tlds));
      return uniqueTlds.map((tld) => `https://logo.clearbit.com/${slug}.${tld}`);
    }
    return [];
  }, [name, website, careersUrl, country]);

  const [idx, setIdx] = useState(0);
  const useLogo = sources.length > 0 && idx < sources.length;

  if (!useLogo) {
    return (
      <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${gradient} text-sm font-bold text-white shadow-sm`}>
        {initials(name)}
      </div>
    );
  }

  return (
    <img
      src={sources[idx]}
      alt={`${name} logo`}
      onError={() => setIdx((i) => i + 1)}
      className="h-11 w-11 shrink-0 rounded-xl bg-white object-contain p-1 shadow-sm ring-1 ring-gray-100"
    />
  );
}
