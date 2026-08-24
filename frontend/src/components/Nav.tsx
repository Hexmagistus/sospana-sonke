"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

const LINKS = [
  { href: "/companies", label: "Companies" },
  { href: "/tailor", label: "Tailor CV" },
  { href: "/profile", label: "Profile" },
  { href: "/cv", label: "CV" },
  { href: "/applications", label: "Applications" },
  { href: "/notifications", label: "Notifications" },
  { href: "/subscription", label: "Subscription" },
  { href: "/security", label: "Security" },
];

export default function Nav() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  if (!user) return null;

  return (
    <nav className="bg-gradient-to-r from-navy via-navy-light to-brand-dark shadow-lg">
      <div className="mx-auto flex max-w-6xl items-center gap-1 px-4 py-2.5 overflow-x-auto">
        <Link href="/companies" className="mr-3 flex items-center gap-2 whitespace-nowrap">
          <span
            className="flex h-8 w-8 items-center justify-center rounded-lg text-sm font-extrabold text-white shadow"
            style={{ background: "conic-gradient(from 210deg,#ff6b5b,#f5b301,#22c58b,#2f9bf6,#7c5cff,#ff6b5b)" }}
          >
            S
          </span>
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
            {l.label}
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
