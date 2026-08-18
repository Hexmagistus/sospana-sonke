"use client";

import { ReactNode } from "react";

type Variant = "dashboard" | "companies" | "tailor" | "jobs";

function RocketArt() {
  return (
    <svg viewBox="0 0 210 150" className="h-full w-full" aria-hidden="true">
      <circle cx="150" cy="60" r="52" fill="rgba(255,255,255,0.06)" />
      <circle cx="40" cy="30" r="3" fill="#ffd76a" />
      <circle cx="70" cy="18" r="2" fill="#fff" opacity="0.8" />
      <circle cx="190" cy="110" r="2.5" fill="#5eead4" />
      <rect x="18" y="96" width="20" height="34" rx="4" fill="#f5b301" />
      <rect x="46" y="78" width="20" height="52" rx="4" fill="#5eead4" />
      <rect x="74" y="58" width="20" height="72" rx="4" fill="#ff6b5b" />
      <g transform="translate(118 34) rotate(8)">
        <path d="M28 0c16 8 26 26 26 48 0 10-4 20-10 27H12C6 68 2 58 2 48 2 26 12 8 28 0Z" fill="#fff" />
        <circle cx="28" cy="34" r="10" fill="#2f9bf6" />
        <circle cx="28" cy="34" r="5" fill="#0b2447" />
        <path d="M12 62c-8 2-12 10-12 20 8 0 14-3 18-8Z" fill="#ff6b5b" />
        <path d="M44 62c8 2 12 10 12 20-8 0-14-3-18-8Z" fill="#ff6b5b" />
        <path d="M20 80c2 8 6 14 8 20 2-6 6-12 8-20Z" fill="#f5b301" />
      </g>
    </svg>
  );
}

function BuildingsArt() {
  return (
    <svg viewBox="0 0 210 150" className="h-full w-full" aria-hidden="true">
      <circle cx="150" cy="58" r="52" fill="rgba(255,255,255,0.06)" />
      <circle cx="40" cy="26" r="3" fill="#ffd76a" />
      <circle cx="185" cy="30" r="2.5" fill="#5eead4" />
      <rect x="40" y="66" width="42" height="72" rx="6" fill="#5eead4" />
      <rect x="90" y="40" width="46" height="98" rx="6" fill="#ffffff" />
      <rect x="144" y="76" width="40" height="62" rx="6" fill="#f5b301" />
      <rect x="111" y="22" width="3" height="20" rx="1.5" fill="#0b2447" />
      <path d="M114 24h16l-5 5 5 5h-16Z" fill="#ff6b5b" />
      {[0, 1, 2].map((r) =>
        [0, 1].map((c) => (
          <rect key={`a${r}${c}`} x={48 + c * 16} y={76 + r * 18} width="9" height="9" rx="2" fill="#0b2447" opacity="0.55" />
        ))
      )}
      {[0, 1, 2, 3].map((r) =>
        [0, 1].map((c) => (
          <rect key={`b${r}${c}`} x={99 + c * 18} y={52 + r * 18} width="10" height="10" rx="2" fill="#2f9bf6" opacity="0.85" />
        ))
      )}
      {[0, 1, 2].map((r) =>
        [0, 1].map((c) => (
          <rect key={`c${r}${c}`} x={151 + c * 15} y={86 + r * 16} width="9" height="9" rx="2" fill="#0b2447" opacity="0.5" />
        ))
      )}
    </svg>
  );
}

function DocumentArt() {
  return (
    <svg viewBox="0 0 210 150" className="h-full w-full" aria-hidden="true">
      <circle cx="150" cy="58" r="52" fill="rgba(255,255,255,0.06)" />
      <rect x="70" y="26" width="78" height="100" rx="10" fill="#5eead4" opacity="0.55" transform="rotate(-6 109 76)" />
      <rect x="78" y="24" width="80" height="104" rx="10" fill="#ffffff" />
      <rect x="90" y="42" width="42" height="8" rx="4" fill="#0b2447" />
      <rect x="90" y="58" width="56" height="6" rx="3" fill="#cbd5e1" />
      <rect x="90" y="70" width="52" height="6" rx="3" fill="#cbd5e1" />
      <rect x="90" y="82" width="56" height="6" rx="3" fill="#cbd5e1" />
      <rect x="90" y="98" width="34" height="10" rx="5" fill="#f5b301" />
      <g transform="translate(120 78) rotate(40)">
        <rect x="0" y="0" width="14" height="60" rx="4" fill="#2f9bf6" />
        <rect x="0" y="0" width="14" height="12" rx="4" fill="#ff6b5b" />
        <path d="M0 60h14l-7 12Z" fill="#ffd76a" />
      </g>
      <path d="M40 40l3 8 8 3-8 3-3 8-3-8-8-3 8-3Z" fill="#ffd76a" />
      <path d="M185 96l2 5 5 2-5 2-2 5-2-5-5-2 5-2Z" fill="#fff" opacity="0.9" />
    </svg>
  );
}

function SearchArt() {
  return (
    <svg viewBox="0 0 210 150" className="h-full w-full" aria-hidden="true">
      <circle cx="150" cy="58" r="52" fill="rgba(255,255,255,0.06)" />
      <rect x="20" y="34" width="118" height="16" rx="5" fill="#ffffff" opacity="0.9" />
      <rect x="20" y="60" width="118" height="16" rx="5" fill="#5eead4" />
      <rect x="20" y="86" width="90" height="16" rx="5" fill="#ffffff" opacity="0.7" />
      <rect x="20" y="112" width="70" height="16" rx="5" fill="#ffffff" opacity="0.5" />
      <g transform="translate(112 58)">
        <circle cx="34" cy="34" r="26" fill="rgba(11,36,71,0.25)" stroke="#f5b301" strokeWidth="8" />
        <rect x="52" y="52" width="38" height="11" rx="5.5" transform="rotate(45 52 52)" fill="#f5b301" />
        <circle cx="34" cy="34" r="12" fill="#ff6b5b" />
      </g>
    </svg>
  );
}

const ART: Record<Variant, ReactNode> = {
  dashboard: <RocketArt />,
  companies: <BuildingsArt />,
  tailor: <DocumentArt />,
  jobs: <SearchArt />,
};

export function Banner({
  variant,
  eyebrow,
  title,
  subtitle,
  children,
}: {
  variant: Variant;
  eyebrow?: string;
  title: string;
  subtitle?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div className="banner relative overflow-hidden rounded-2xl bg-gradient-to-br from-navy via-navy-light to-brand p-6 text-white shadow-lg sm:p-8">
      <div className="pointer-events-none absolute -right-10 -top-16 h-52 w-52 rounded-full bg-gold/20 blur-xl" />
      <div className="pointer-events-none absolute -bottom-16 left-24 h-40 w-40 rounded-full bg-coral/20 blur-xl" />
      <div className="relative flex items-center justify-between gap-4">
        <div className="max-w-xl">
          {eyebrow && (
            <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-gold">{eyebrow}</p>
          )}
          <h1 className="text-2xl font-extrabold sm:text-3xl">{title}</h1>
          {subtitle && <p className="mt-2 text-sm text-blue-100 sm:text-base">{subtitle}</p>}
          {children && <div className="mt-4">{children}</div>}
        </div>
        <div className="hidden h-32 w-52 shrink-0 sm:block">{ART[variant]}</div>
      </div>
    </div>
  );
}
