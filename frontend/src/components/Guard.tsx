"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { FunSpinner } from "./FunSpinner";

/**
 * Sign-in is switched off, so ordinary pages are public: Guard renders them for everyone.
 * Admin-only tools stay hidden; anyone who is not an existing signed-in admin is sent home.
 */
export default function Guard({ children, admin = false }: { children: React.ReactNode; admin?: boolean }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const blocked = admin && !loading && (!user || user.role !== "admin");

  useEffect(() => {
    if (blocked) router.replace("/");
  }, [blocked, router]);

  if (!admin) return <>{children}</>;
  if (loading) return <FunSpinner />;
  if (blocked) return null;
  return <>{children}</>;
}
