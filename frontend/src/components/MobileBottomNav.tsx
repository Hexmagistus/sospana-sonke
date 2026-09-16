"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

// A thumb-reachable bottom tab bar for small screens, mirroring the top Nav's
// most-used destinations (Home / Search / Saved / Applications / Profile) so
// mobile users aren't stuck reaching for a hamburger menu for every trip
// between the core sections. Desktop/tablet keeps using the existing top Nav
// (hidden here via `md:hidden`); nothing here replaces it.

type Item = {
  href: string;
  label: string;
  // Matches this tab as "active" for any path starting with `match`
  // (falls back to `href`) so nested routes (e.g. /matches/[id]) still light
  // up the right tab.
  match?: string;
  icon: (active: boolean) => React.ReactNode;
};

function iconProps(active: boolean) {
  return {
    viewBox: "0 0 24 24",
    className: "h-5 w-5",
    fill: "none" as const,
    stroke: "currentColor",
    strokeWidth: active ? 2.25 : 1.75,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
}

const ITEMS: Item[] = [
  {
    href: "/dashboard",
    label: "Home",
    icon: (a) => (
      <svg {...iconProps(a)} aria-hidden="true">
        <path d="M3 11.5 12 4l9 7.5" />
        <path d="M5.5 9.5V19a1 1 0 0 0 1 1H9a1 1 0 0 0 1-1v-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v4a1 1 0 0 0 1 1h2.5a1 1 0 0 0 1-1V9.5" />
      </svg>
    ),
  },
  {
    href: "/agent",
    label: "Search",
    icon: (a) => (
      <svg {...iconProps(a)} aria-hidden="true">
        <circle cx="11" cy="11" r="6.5" />
        <path d="m20 20-3.5-3.5" />
      </svg>
    ),
  },
  {
    href: "/matches",
    label: "Saved",
    match: "/matches",
    icon: (a) => (
      <svg {...iconProps(a)} aria-hidden="true">
        <path d="M6 3.5h12a1 1 0 0 1 1 1V21l-7-4-7 4V4.5a1 1 0 0 1 1-1Z" />
      </svg>
    ),
  },
  {
    href: "/tailor/applications",
    label: "Applications",
    match: "/tailor/applications",
    icon: (a) => (
      <svg {...iconProps(a)} aria-hidden="true">
        <rect x="4.5" y="3.5" width="15" height="17" rx="2" />
        <path d="M8.5 8h7M8.5 12h7M8.5 16h4" />
      </svg>
    ),
  },
  {
    href: "/profile",
    label: "Profile",
    icon: (a) => (
      <svg {...iconProps(a)} aria-hidden="true">
        <circle cx="12" cy="8.5" r="3.5" />
        <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
      </svg>
    ),
  },
];

export default function MobileBottomNav() {
  const { user } = useAuth();
  const pathname = usePathname();

  if (!user) return null;

  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-ss-border bg-ss-glass backdrop-blur-md md:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="mx-auto flex max-w-6xl items-stretch justify-between px-1">
        {ITEMS.map((item) => {
          const active = pathname === item.href || (item.match ? pathname.startsWith(item.match) : false);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-label={item.label}
              aria-current={active ? "page" : undefined}
              className={`relative flex flex-1 flex-col items-center justify-center gap-0.5 py-2 text-[11px] font-medium transition ${
                active ? "text-ss-primary" : "text-ss-muted hover:text-ss-text"
              }`}
            >
              {item.icon(active)}
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
