"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { useTheme } from "@/lib/theme";
import NotificationBell from "@/components/NotificationBell";
import { isExplorerPath, OPEN_MENU_EVENT } from "@/lib/explorer/explorerPaths";

const LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/agent", label: "Career Agent" },
  { href: "/applications", label: "My Applications" },
  { href: "/companies", label: "Companies" },
  { href: "/universities", label: "Universities" },
  { href: "/colleges", label: "Colleges" },
  { href: "/hospitals", label: "Hospitals" },
  { href: "/companies?type=SETA", label: "SETAs" },
  { href: "/tailor", label: "CV Builder" },
  { href: "/profile", label: "Profile" },
  { href: "/preferences", label: "Preferences" },
  { href: "/messages", label: "Messages" },
  { href: "/notifications", label: "Notifications" },
  { href: "/security", label: "Security" },
  { href: "/donate", label: "Donate" },
];

/** Sun/moon toggle -- a real, functional light/dark switch (brief section 26),
 * not decoration. The gold caption sits under the icon on desktop and mobile.
 * aria-label and the tooltip keep the action ("switch to light/dark mode"). */
function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, toggleTheme } = useTheme();
  const hint = theme === "dark"
    ? "Adjust brightness. Switch to light mode"
    : "Adjust brightness. Switch to dark mode";
  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={hint}
      title={hint}
      className={`flex min-h-11 w-9 shrink-0 flex-col items-center justify-center gap-0.5 rounded-md px-0.5 py-0.5 text-ss-primary min-[380px]:w-[4.5rem] min-[430px]:w-[5.25rem] transition hover:bg-ss-primary-soft hover:text-ss-text ${className}`}
    >
      <span className="flex h-7 w-7 items-center justify-center" aria-hidden="true">
        {theme === "dark" ? (
          <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="4.5" />
            <path strokeLinecap="round" d="M12 2.5v2M12 19.5v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M2.5 12h2M19.5 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M20.5 14.5A8.5 8.5 0 019.5 3.5a8.5 8.5 0 1011 11z" />
          </svg>
        )}
      </span>
      <span className="hidden w-full whitespace-normal text-center text-[11px] min-[380px]:block font-semibold leading-tight tracking-tight text-ss-primary">
        Adjust brightness
      </span>
    </button>
  );
}

export default function Nav() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [unread, setUnread] = useState(0);
  const [unreadMsgs, setUnreadMsgs] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  // Desktop drawer for the explorer pages, which have no top bar from `lg` up.
  const [drawerOpen, setDrawerOpen] = useState(false);
  const explorer = isExplorerPath(pathname);

  // Keep the Notifications link's badge current: poll while logged in, and
  // refresh immediately whenever the notifications page marks something read
  // (it dispatches this event) or the user navigates between pages.
  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    async function refresh() {
      try {
        const res = await api.get<{ unread: number }>("/notifications/unread-count");
        if (!cancelled) setUnread(res.unread);
      } catch {
        // a missed poll shouldn't disrupt navigation
      }
    }
    async function refreshMsgs() {
      try {
        const res = await api.get<{ unread: number }>("/messages/unread-count");
        if (!cancelled) setUnreadMsgs(res.unread);
      } catch {
        // a missed poll shouldn't disrupt navigation
      }
    }
    refresh();
    refreshMsgs();
    const id = setInterval(() => { refresh(); refreshMsgs(); }, 30000);
    window.addEventListener("notifications:changed", refresh);
    window.addEventListener("messages:changed", refreshMsgs);
    return () => {
      cancelled = true;
      clearInterval(id);
      window.removeEventListener("notifications:changed", refresh);
      window.removeEventListener("messages:changed", refreshMsgs);
    };
  }, [user, pathname]);

  // Close the mobile menu on every navigation so it doesn't stay open
  // when the user taps a link and lands on the new page.
  useEffect(() => {
    setMenuOpen(false);
    setDrawerOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!explorer) return;
    const open = () => setDrawerOpen(true);
    window.addEventListener(OPEN_MENU_EVENT, open);
    return () => window.removeEventListener(OPEN_MENU_EVENT, open);
  }, [explorer]);

  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setDrawerOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [drawerOpen]);

  if (!user) return null;

  const linkClass = (active: boolean) =>
    `rounded-md px-2 py-1.5 text-sm whitespace-nowrap transition xl:px-3 ${
      active ? "bg-gold font-semibold text-navy shadow-sm" : "text-ss-text hover:bg-ss-primary-soft"
    }`;

  const renderLink = (l: (typeof LINKS)[number], onClick?: () => void) => (
    <Link key={l.href} href={l.href} onClick={onClick} className={linkClass(pathname === l.href)}>
      {(l.href === "/notifications" && unread > 0) || (l.href === "/messages" && unreadMsgs > 0) ? (
        <span className="inline-flex items-center gap-1.5">
          {l.label}
          <span className="inline-flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-red-700 px-1 text-[10px] font-bold leading-none text-white">
            {(() => { const n = l.href === "/messages" ? unreadMsgs : unread; return n > 9 ? "9+" : n; })()}
          </span>
        </span>
      ) : (
        l.label
      )}
    </Link>
  );

  return (
    <>
    <nav className={`sticky top-0 z-30 border-b-2 border-gold bg-ss-surface shadow-[0_8px_24px_-18px_rgba(11,36,71,0.5)] ${explorer ? "lg:hidden" : ""}`}>
      <div className="mx-auto flex w-full max-w-6xl items-center gap-1 px-3 py-2.5 min-[360px]:px-4">
        <Link href="/companies" className="mr-1 flex shrink-0 items-center gap-1.5 whitespace-nowrap min-[360px]:gap-2 sm:mr-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo-mark.png" alt="Sospana Sonke" className="block h-8 w-8 max-w-none shrink-0 aspect-square rounded-xl min-[360px]:h-9 min-[360px]:w-9 object-cover shadow-[0_0_22px_-2px_var(--ss-primary-glow)] ring-1 ring-gold/50" />
          <span className="text-[0.9rem] font-bold text-ss-text min-[360px]:text-base">Sospana&nbsp;Sonke</span>
        </Link>

        {/* Desktop / tablet: full link row */}
        <div className="hidden min-w-0 flex-1 flex-wrap items-center gap-x-0.5 gap-y-1 lg:flex xl:gap-x-1">
          {LINKS.map((l) => renderLink(l))}
          {user.role === "admin" && (
            <Link href="/admin" className={linkClass(pathname.startsWith("/admin"))}>
              Admin
            </Link>
          )}
          <div className="ml-auto flex shrink-0 items-center gap-3 whitespace-nowrap pl-2">
            <NotificationBell unread={unread} />
            <ThemeToggle />
            <span className="hidden max-w-[9rem] truncate text-xs text-ss-muted xl:inline" title={user.email}>{user.email}</span>
            <button
              onClick={() => {
                logout();
                router.push("/login");
              }}
              className="text-sm font-semibold text-ss-text underline-offset-2 hover:underline"
            >
              Sign out
            </button>
          </div>
        </div>

        {/* Mobile: theme toggle + hamburger, pushed to the right */}
        <div className="ml-auto flex items-center gap-0 min-[360px]:gap-1 lg:hidden">
          <NotificationBell unread={unread} />
          <ThemeToggle />
          <button
            type="button"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((v) => !v)}
            className="flex h-11 w-11 items-center justify-center rounded-md text-ss-text hover:bg-ss-primary-soft lg:h-9 lg:w-9"
          >
            {menuOpen ? (
              <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 6l12 12M18 6L6 18" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 7h16M4 12h16M4 17h16" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Mobile: stacked dropdown panel */}
      {menuOpen && (
        <div className="border-t border-ss-border px-4 pb-3 pt-2 lg:hidden">
          <div className="flex flex-col gap-1">
            {LINKS.map((l) => renderLink(l, () => setMenuOpen(false)))}
            {user.role === "admin" && (
              <Link
                href="/admin"
                onClick={() => setMenuOpen(false)}
                className={linkClass(pathname.startsWith("/admin"))}
              >
                Admin
              </Link>
            )}
          </div>
          <div className="mt-3 flex items-center justify-between border-t border-ss-border pt-3">
            <span className="truncate text-xs text-ss-muted">{user.email}</span>
            <button
              onClick={() => {
                logout();
                router.push("/login");
              }}
              className="text-sm font-semibold text-ss-text underline-offset-2 hover:underline"
            >
              Sign out
            </button>
          </div>
        </div>
      )}
    </nav>

    {/* Desktop explorer pages: the same links, in a drawer opened by the Menu button beside the logo. */}
    {explorer && drawerOpen && (
      <div className="fixed inset-0 z-50 hidden lg:block" onMouseDown={(e) => { if (e.target === e.currentTarget) setDrawerOpen(false); }}>
        <div className="absolute inset-0 bg-slate-900/40" aria-hidden="true" onMouseDown={() => setDrawerOpen(false)} />
        <aside
          role="dialog"
          aria-modal="true"
          aria-label="Site menu"
          className="absolute left-0 top-0 flex h-full w-72 flex-col overflow-y-auto border-r border-ss-border bg-ss-surface p-4 shadow-2xl"
        >
          <div className="mb-3 flex items-center justify-between">
            <span className="flex items-center gap-2 font-bold text-ss-text">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo-mark.png" alt="" className="h-8 w-8 rounded-lg object-cover ring-1 ring-gold/50" />
              Sospana&nbsp;Sonke
            </span>
            <button
              type="button"
              autoFocus
              aria-label="Close menu"
              onClick={() => setDrawerOpen(false)}
              className="flex h-8 w-8 items-center justify-center rounded-md text-ss-text hover:bg-ss-primary-soft"
            >
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M6 6l12 12M18 6L6 18" /></svg>
            </button>
          </div>
          <div className="flex flex-col gap-1">
            {LINKS.map((l) => renderLink(l, () => setDrawerOpen(false)))}
            {user.role === "admin" && (
              <Link href="/admin" onClick={() => setDrawerOpen(false)} className={linkClass(pathname.startsWith("/admin"))}>
                Admin
              </Link>
            )}
          </div>
          <div className="mt-4 flex items-center gap-3 border-t border-ss-border pt-3">
            <NotificationBell unread={unread} />
            <ThemeToggle />
          </div>
          <div className="mt-3 flex items-center justify-between gap-2">
            <span className="min-w-0 truncate text-xs text-ss-muted" title={user.email}>{user.email}</span>
            <button
              onClick={() => {
                logout();
                router.push("/login");
              }}
              className="shrink-0 text-sm font-semibold text-ss-text underline-offset-2 hover:underline"
            >
              Sign out
            </button>
          </div>
        </aside>
      </div>
    )}
    </>
  );
}
