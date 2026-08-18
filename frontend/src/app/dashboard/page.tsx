"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// The dashboard has been removed. Anyone landing here (old links/bookmarks) is
// sent to Find jobs, which is now the app's home screen.
export default function DashboardRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/jobs");
  }, [router]);
  return null;
}
