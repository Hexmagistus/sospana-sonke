"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { API_BASE } from "@/lib/api";

export const AUTH_PAUSED_MESSAGE =
  "Sign-in is paused during maintenance. You can still browse today's jobs, no account needed.";

/** True when an auth error means the database is down (503 maintenance or a DB error). */
export function isMaintenanceError(err: unknown): boolean {
  const status = (err as { status?: number } | null)?.status;
  const msg = err instanceof Error ? err.message : String(err ?? "");
  return status === 503 || /maintenance|database|quota|operationalerror/i.test(msg);
}

/**
 * Sign-in is paused when the device is offline or /status reports the database down.
 * `pause()` lets a failed auth request (503 / DB error) switch the page over too.
 */
export function useAuthPaused(): { paused: boolean; pause: () => void } {
  const [offline, setOffline] = useState(false);
  const [dbDown, setDbDown] = useState(false);
  useEffect(() => {
    const sync = () => setOffline(typeof navigator !== "undefined" && navigator.onLine === false);
    sync();
    window.addEventListener("online", sync);
    window.addEventListener("offline", sync);
    let cancelled = false;
    fetch(`${API_BASE}/status`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!cancelled && d && (d.status === "down" || d.components?.database?.status === "down")) setDbDown(true);
      })
      .catch(() => { /* unreachable API: the offline flag or a failed submit covers it */ });
    return () => {
      cancelled = true;
      window.removeEventListener("online", sync);
      window.removeEventListener("offline", sync);
    };
  }, []);
  const pause = useCallback(() => setDbDown(true), []);
  return { paused: offline || dbDown, pause };
}

export function AuthMaintenanceBanner() {
  return (
    <div
      role="status"
      className="mb-4 rounded-2xl border-2 border-[#f5b301] bg-[#fff8e1] p-4 text-center text-[#0b2447] shadow-md"
    >
      <p className="mb-3 text-base font-bold">🛠️ {AUTH_PAUSED_MESSAGE}</p>
      <Link
        href="/jobs"
        className="inline-block rounded-xl bg-[#0b2447] px-6 py-3 text-base font-extrabold text-[#f5b301] shadow hover:bg-[#13315c]"
      >
        Browse jobs
      </Link>
    </div>
  );
}
