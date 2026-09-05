"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

const LINKS = [
  { href: "/jobs", label: "Find jobs" },
  { href: "/companies", label: "Companies" },
  { href: "/profile", label: "Profile" },
  { href: "/notifications", label: "Notifications" },
  { href: "/security", label: "Security" },
];

export default function Nav() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [unread, setUnread] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);

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
    refresh();
    const id = setInterval(refresh, 30000);
    window.addEventListener("notifications:changed", refresh);
    return () => {
      cancelled = true;
      clearInterval(id);
      window.removeEventListener("notifications:changed", refresh);
    };
  }, [user, pathname]);

  // Close the mobile menu on every navigation so it doesn't stay open
  // when the user taps a link and lands on the new page.
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  if (!user) return null;

  const linkClass = (active: boolean) =>
    `rounded-md px-3 py-1.5 text-sm whitespace-nowrap transition ${
      active ? "bg-gold font-semibold text-navy shadow-sm" : "text-blue-100 hover:bg-white/10 hover:text-white"
    }`;

  const renderLink = (l: (typeof LINKS)[number], onClick?: () => void) => (
    <Link key={l.href} href={l.href} onClick={onClick} className={linkClass(pathname === l.href)}>
      {l.href === "/notifications" && unread > 0 ? (
        <span className="inline-flex items-center gap-1.5">
          {l.label}
          <span className="inline-flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold leading-none text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        </span>
      ) : (
        l.label
      )}
    </Link>
  );

  return (
    <nav className="bg-gradient-to-r from-navy via-navy-light to-brand-dark shadow-lg">
      <div className="mx-auto flex max-w-6xl items-center gap-1 px-4 py-2.5">
        <Link href="/companies" className="mr-3 flex items-center gap-2 whitespace-nowrap">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo-mark.png" alt="Sospana Sonke" className="h-8 w-8 rounded-lg object-cover shadow" />
          <span className="font-bold text-white">Sospana&nbsp;Sonke</span>
        </Link>

        {/* Desktop / tablet: full link row */}
        <div className="hidden flex-1 items-center gap-1 md:flex">
          {LINKS.map((l) => renderLink(l))}
          {user.role === "admin" && (
            <Link href="/admin" className={linkClass(pathname.startsWith("/admin"))}>
              Admin
            </Link>
          )}
          <div className="ml-auto flex items-center gap-3 whitespace-nowrap">
            <span className="text-xs text-blue-200">{user.email}</span>
            <button
              onClick={() => {
                logout();
                router.push("/login");
              }}
              className="text-sm text-blue-100 hover:text-white"
            >
              Sign out
            </button>
          </div>
        </div>

        {/* Mobile: hamburger toggle, pushed to the right */}
        <button
          type="button"
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((v) => !v)}
          className="ml-auto flex h-9 w-9 items-center justify-center rounded-md text-white hover:bg-white/10 md:hidden"
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

      {/* Mobile: stacked dropdown panel */}
      {menuOpen && (
        <div className="border-t border-white/10 px-4 pb-3 pt-2 md:hidden">
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
          <div className="mt-3 flex items-center justify-between border-t border-white/10 pt-3">
            <span className="truncate text-xs text-blue-200">{user.email}</span>
            <button
              onClick={() => {
                logout();
                router.push("/login");
              }}
              className="text-sm text-blue-100 hover:text-white"
            >
              Sign out
            </button>
          </div>
        </div>
      )}
    </nav>
  );
}
