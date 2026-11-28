"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";

// Counts page views even when the backend or the device is offline: each view is queued in
// localStorage and sent to /api/visit (which does not use Neon) when it can be. Failed sends
// stay queued and are retried on the next page view or when the device comes back online.
const KEY = "ss_visit_queue";
const MAX = 500;

type Visit = { day: string; path: string };

function load(): Visit[] {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) || "[]");
    return Array.isArray(v) ? v : [];
  } catch {
    return [];
  }
}

function save(q: Visit[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(q.slice(-MAX)));
  } catch {
    /* storage full or blocked: drop silently */
  }
}

let flushing = false;
async function flush() {
  if (flushing || (typeof navigator !== "undefined" && navigator.onLine === false)) return;
  const batch = load().slice(0, 200);
  if (batch.length === 0) return;
  flushing = true;
  try {
    const res = await fetch("/api/visit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ visits: batch }),
      keepalive: true,
    });
    if (res.ok) save(load().slice(batch.length));
  } catch {
    /* offline: keep the queue */
  } finally {
    flushing = false;
  }
}

export default function VisitCounter() {
  const pathname = usePathname();
  useEffect(() => {
    if (!pathname || navigator.webdriver || pathname.startsWith("/stats")) return;
    const day = new Date().toLocaleDateString("en-CA", { timeZone: "Africa/Johannesburg" });
    save([...load(), { day, path: pathname }]);
    void flush();
  }, [pathname]);
  useEffect(() => {
    const on = () => void flush();
    window.addEventListener("online", on);
    return () => window.removeEventListener("online", on);
  }, []);
  return null;
}
