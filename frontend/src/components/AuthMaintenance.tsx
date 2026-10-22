"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { API_BASE } from "@/lib/api";
import { SA_CAREERS_ENABLED } from "@/lib/maintenance";

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
      className="mb-4 rounded-2xl border-2 border-[#FCC033] bg-[#fff8e1] p-4 text-center text-[#07284C] shadow-md"
    >
      <p className="mb-3 text-base font-bold">🛠️ {AUTH_PAUSED_MESSAGE}</p>
      <Link
        href="/jobs"
        className="inline-block rounded-xl bg-[#07284C] px-6 py-3 text-base font-extrabold text-[#FCC033] shadow hover:bg-[#0D3A66]"
      >
        Browse jobs
      </Link>
    </div>
  );
}

/** Site-wide banner, top of every page, while the database is down or the device is offline. */
export function SiteMaintenanceBanner() {
  const { paused } = useAuthPaused();
  if (!paused) return null;
  return (
    <div role="status" className="w-full border-b-4 border-[#FCC033] bg-[#07284C] px-4 py-4 text-center text-white sm:py-5">
      <p className="mx-auto max-w-3xl text-lg font-extrabold leading-snug sm:text-2xl">
        🛠️ <span className="text-[#FCC033]">Under maintenance:</span> we&apos;re upgrading our servers. You can still browse
        today&apos;s checked jobs, no account needed.
      </p>
      <Link
        href="/jobs"
        className="mt-3 inline-block rounded-2xl bg-[#FD6948] px-8 py-3 text-lg font-extrabold text-[#07284C] shadow-lg hover:bg-[#FF7D60] sm:text-xl"
      >
        Browse jobs
      </Link>
      {SA_CAREERS_ENABLED && (
        // TEMPORARY maintenance link, see src/lib/maintenance.ts
        <Link
          href="/sa-careers"
          className="ml-0 mt-3 inline-block rounded-2xl border-2 border-[#FCC033] bg-white px-8 py-3 text-lg font-extrabold text-[#07284C] shadow-lg hover:bg-[#fff8e1] sm:ml-3 sm:text-xl"
        >
          🇿🇦 SA careers pages
        </Link>
      )}
      {SA_CAREERS_ENABLED && (
        <Link
          href="/offline-guide"
          className="ml-0 mt-3 inline-block rounded-2xl border-2 border-[#FCC033] bg-white px-8 py-3 text-lg font-extrabold text-[#07284C] shadow-lg hover:bg-[#fff8e1] sm:ml-3 sm:text-xl"
        >
          📘 Offline guide
        </Link>
      )}
    </div>
  );
}
