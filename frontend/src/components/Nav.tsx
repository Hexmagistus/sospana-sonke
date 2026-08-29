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
  { href: "/cv", label: "CV" },
  { href: "/applications", label: "Applications" },
  { href: "/notifications", label: "Notifications" },
  { href: "/security", label: "Security" },
];

export default function Nav() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [unread, setUnread] = useState(0);

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

  if (!user) return null;

  return (
    <nav className="bg-gradient-to-r from-navy via-navy-light to-brand-dark shadow-lg">
      <div className="mx-auto flex max-w-6xl items-center gap-1 px-4 py-2.5 overflow-x-auto">
        <Link href="/companies" className="mr-3 flex items-center gap-2 whitespace-nowrap">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo-mark.png" alt="Sospana Sonke" className="h-8 w-8 rounded-lg object-cover shadow" />
          <span className="font-bold text-white">Sospana&nbsp;Sonke</span>
        </Link>
        {LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={`rounded-md px-3 py-1.5 text-sm whitespace-nowrap transition ${
              pathname === l.href
                ? "bg-gold font-semibold text-navy shadow-sm"
                : "text-blue-100 hover:bg-white/10 hover:text-white"
            }`}
          >
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
        ))}
        {user.role === "admin" && (
          <Link
            href="/admin"
            className={`rounded-md px-3 py-1.5 text-sm whitespace-nowrap transition ${
              pathname.startsWith("/admin")
                ? "bg-gold font-semibold text-navy shadow-sm"
                : "text-blue-100 hover:bg-white/10 hover:text-white"
            }`}
          >
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
    </nav>
  );
}
