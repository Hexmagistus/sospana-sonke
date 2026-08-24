"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Spinner } from "./ui";

export default function Guard({ children, admin = false }: { children: React.ReactNode; admin?: boolean }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
    if (!loading && user && admin && user.role !== "admin") router.replace("/companies");
  }, [loading, user, admin, router]);

  if (loading) return <div className="p-8"><Spinner /></div>;
  if (!user) return null;
  if (admin && user.role !== "admin") return null;
  return <>{children}</>;
}
