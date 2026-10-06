"use client";

import { useEffect, useMemo, useState } from "react";
import { API_BASE } from "@/lib/api";
import { companyIconSrc } from "@/lib/companyIcon";
import { DATA_SAVER_EVENT, isDataSaver } from "@/lib/dataSaver";
import { monogramColours, monogramInitials } from "@/lib/monogram";

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

export function CompanyLogo({
  name,
  website,
  careersUrl,
  country,
  logoUrl,
  id,
  hasIcon = false,
  iconVersion,
}: {
  name: string;
  website?: string | null;
  careersUrl?: string | null;
  country?: string | null;
  gradient?: string;
  // An explicit, verified logo image URL taken directly from the entity's own
  // official website. When set, it's tried first — ahead of the stored icon —
  // since it's a real confirmed logo, not a guess.
  logoUrl?: string | null;
  // The company's id. The icon URL is requested only when hasIcon is true,
  // because a directory of cards used to call GET /companies/{id}/icon for
  // every employer and the misses came back as uncached 404s.
  id?: string | null;
  hasIcon?: boolean;
  // From the API (icon_version). Sent as ?v= so the icon URL changes when the
  // icon does, which lets the API mark the response immutable for a year.
  iconVersion?: number | null;
}) {
  // Order: a manually-verified logo first, then the icon OUR API stores for this
  // company (fetched once, server-side, from the company's own site), then the
  // monogram badge. The browser never asks Clearbit, Google or any other third
  // party for a logo, so a page of cards causes no outbound flood.
  const sources = useMemo(() => {
    const chain: string[] = [];
    if (logoUrl) chain.push(logoUrl);
    const stored = companyIconSrc(API_BASE, id, hasIcon, iconVersion);
    if (stored) chain.push(stored);
    return chain;
  }, [logoUrl, id, hasIcon, iconVersion]);

  const [idx, setIdx] = useState(0);
  const [saver, setSaver] = useState(false);
  useEffect(() => {
    const sync = () => setSaver(isDataSaver());
    sync();
    window.addEventListener(DATA_SAVER_EVENT, sync);
    return () => window.removeEventListener(DATA_SAVER_EVENT, sync);
  }, []);
  const useLogo = !saver && sources.length > 0 && idx < sources.length;

  if (!useLogo) {
    // Guaranteed fallback: initials on brand navy/gold, colour fixed by the
    // company so it never changes between visits. `gradient` is kept in the props
    // so existing callers compile unchanged; the badge no longer needs it.
    const c = monogramColours(id || name);
    const initials = monogramInitials(name);
    return (
      <div
        role="img"
        aria-label={`${name} (initials badge)`}
        className="ss-monogram flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-sm font-bold tracking-tight shadow-sm"
        style={{ backgroundColor: c.bg, color: c.fg, boxShadow: `inset 0 0 0 1.5px ${c.ring}55` }}
      >
        <span aria-hidden="true">{initials}</span>
      </div>
    );
  }

  return (
    <img
      src={sources[idx]}
      alt={`${name} logo`}
      // Only cards scrolled into (or near) view request their icon, so a long
      // directory page no longer fires 100+ icon requests at once.
      loading="lazy"
      decoding="async"
      width={44}
      height={44}
      onError={() => setIdx((i) => i + 1)}
      className="h-11 w-11 shrink-0 rounded-xl bg-ss-surface object-contain p-1 shadow-sm ring-1 ring-gray-100"
    />
  );
}
