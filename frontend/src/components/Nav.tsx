"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

const LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/profile", label: "Profile" },
  { href: "/cv", label: "CV" },
  { href: "/companies", label: "Companies" },
  { href: "/matches", label: "Matches" },
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
    <nav className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center gap-1 px-4 py-2 overflow-x-auto">
        <Link href="/dashboard" className="mr-3 font-semibold text-brand whitespace-nowrap">
          Sospana&nbsp;Sonke
        </Link>
        {LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={`rounded-md px-3 py-1.5 text-sm whitespace-nowrap ${
              pathname === l.href ? "bg-brand/10 text-brand" : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            {l.label}
          </Link>
        ))}
        {user.role === "admin" && (
          <Link
            href="/admin"
            className={`rounded-md px-3 py-1.5 text-sm whitespace-nowrap ${
              pathname.startsWith("/admin") ? "bg-brand/10 text-brand" : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            Admin
          </Link>
        )}
        <div className="ml-auto flex items-center gap-3 whitespace-nowrap">
          <span className="text-xs text-gray-500">{user.email}</span>
          <button
            onClick={() => {
              logout();
              router.push("/login");
            }}
            className="text-sm text-gray-500 hover:text-gray-800"
          >
            Sign out
          </button>
        </div>
      </div>
    </nav>
  );
}
