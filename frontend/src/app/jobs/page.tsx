"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// The standalone "Find jobs" page has been retired — job search now lives inside
// the Companies tab. Redirect any old links/bookmarks there.
export default function JobsRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/companies");
  }, [router]);
  return null;
}
