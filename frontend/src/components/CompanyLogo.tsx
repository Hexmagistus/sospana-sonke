"use client";

import { useMemo, useState } from "react";

// Careers links that sit on a third-party ATS / job board — their favicon is the
// platform's logo, not the employer's, so we never take the logo from these.
const ATS_DOMAINS = [
  "myworkdayjobs.com", "workday.com", "wd1.myworkdaysite.com", "wd3.myworkdayjobs.com",
  "successfactors.com", "sapsf.com", "oraclecloud.com", "taleo.net",
  "greenhouse.io", "lever.co", "smartrecruiters.com", "workable.com",
  "erecruit.co", "erecruit.co.za", "mcidirecthire.com", "pnet.co.za", "careers24.com",
  "simplify.hr", "jobvite.com", "icims.com", "bamboohr.com", "breezy.hr",
  "recruitmentportal.co.za", "ci.hr", "placementpartner.co.za", "mnetjobs.com",
];

const COMPANY_SUFFIXES = /\b(ltd|limited|pty|proprietary|holdings?|group|soc|inc|incorporated|corporation|corp|company|co|plc|rf|sa|the)\b/gi;

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
  gradient,
}: {
  name: string;
  website?: string | null;
  careersUrl?: string | null;
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
    // so a wrong brand is never shown).
    const slug = slugFromName(name);
    if (slug.length >= 3) {
      return [`https://logo.clearbit.com/${slug}.co.za`, `https://logo.clearbit.com/${slug}.com`];
    }
    return [];
  }, [name, website, careersUrl]);

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
