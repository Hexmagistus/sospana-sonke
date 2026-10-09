"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Alert } from "./ui";
import { FunSpinner } from "./FunSpinner";

export default function Guard({ children, admin = false }: { children: React.ReactNode; admin?: boolean }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const adminNeedsMfa = Boolean(user && admin && user.role === "admin" && !user.mfa_enabled);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
    if (!loading && user && admin && user.role !== "admin") router.replace("/companies");
    if (!loading && adminNeedsMfa) router.replace("/security");
  }, [loading, user, admin, adminNeedsMfa, router]);

  if (loading) return <FunSpinner />;
  if (!user) return null;
  if (admin && user.role !== "admin") return null;
  if (adminNeedsMfa) return null;
  if (!user.email_verified && !pathname.startsWith("/security")) {
    return (
      <div className="mx-auto max-w-lg px-4 py-10">
        <Alert kind="info">
          Open the verification link from your email before using the directory.
          You can still export or delete this account from Security.
        </Alert>
        <p className="mt-4 text-sm">
          <Link href="/security" className="font-semibold text-ss-primary underline">Open Security</Link>
        </p>
      </div>
    );
  }
  return <>{children}</>;
}
