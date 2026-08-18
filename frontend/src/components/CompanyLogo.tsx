"use client";

import { useMemo, useState } from "react";

// Careers links that sit on a third-party ATS / job board — their favicon is the
// platform's logo, not the employer's, so we skip logos and show initials instead.
const ATS_DOMAINS = [
  "myworkdayjobs.com", "workday.com", "wd1.myworkdaysite.com", "wd3.myworkdayjobs.com",
  "successfactors.com", "sapsf.com", "oraclecloud.com", "taleo.net",
  "greenhouse.io", "lever.co", "smartrecruiters.com", "workable.com",
  "erecruit.co.za", "mcidirecthire.com", "pnet.co.za", "careers24.com",
  "simplify.hr", "jobvite.com", "icims.com", "bamboohr.com", "breezy.hr",
  "recruitmentportal.co.za", "ci.hr", "placementpartner.co.za", "mnetjobs.com",
];

function domainFrom(url?: string | null): string | null {
  if (!url) return null;
  try {
    const u = new URL(url.startsWith("http") ? url : `https://${url}`);
    return u.hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return null;
  }
}

export function isAtsPortal(url?: string | null): boolean {
  const d = domainFrom(url);
  return !!d && ATS_DOMAINS.some((x) => d === x || d.endsWith(`.${x}`));
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
  const domain = domainFrom(website) || domainFrom(careersUrl);
  const isATS = !!domain && ATS_DOMAINS.some((d) => domain === d || domain.endsWith(`.${d}`));

  const sources = useMemo(() => {
    if (!domain || isATS) return [];
    return [
      `https://logo.clearbit.com/${domain}`,
      `https://www.google.com/s2/favicons?domain=${domain}&sz=128`,
    ];
  }, [domain, isATS]);

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
