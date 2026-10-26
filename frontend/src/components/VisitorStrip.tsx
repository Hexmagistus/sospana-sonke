"use client";

import { useEffect, useState } from "react";
import { VISITOR_STRIP_ENABLED } from "@/lib/maintenance";

// TEMPORARY maintenance strip, gated by VISITOR_STRIP_ENABLED (src/lib/maintenance.ts).
// Shows real totals from GET /api/visit (counts only, no personal data). Hidden while offline,
// while loading, and whenever the server has no real numbers to give.
type Summary = { views: number; visitors: number; since: string | null };

function sinceLabel(day: string | null): string {
  if (!day) return "";
  const d = new Date(`${day}T12:00:00Z`);
  if (Number.isNaN(d.getTime())) return "";
  return ` since ${d.toLocaleDateString("en-ZA", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })}`;
}

export default function VisitorStrip() {
  const [data, setData] = useState<Summary | null>(null);
  const [online, setOnline] = useState(true);

  useEffect(() => {
    if (!VISITOR_STRIP_ENABLED) return;
    const sync = () => setOnline(navigator.onLine !== false);
    sync();
    window.addEventListener("online", sync);
    window.addEventListener("offline", sync);
    return () => {
      window.removeEventListener("online", sync);
      window.removeEventListener("offline", sync);
    };
  }, []);

  useEffect(() => {
    if (!VISITOR_STRIP_ENABLED || !online) return;
    let cancelled = false;
    fetch("/api/visit", { headers: { Accept: "application/json" } })
      .then((r) => (r.status === 200 ? r.json() : null))
      .then((d) => {
        if (cancelled || !d) return;
        const ok = Number.isFinite(d.views) && Number.isFinite(d.visitors) && d.views > 0 && d.visitors > 0;
        if (ok) setData({ views: d.views, visitors: d.visitors, since: typeof d.since === "string" ? d.since : null });
      })
      .catch(() => { /* offline or blocked: stay hidden */ });
    return () => {
      cancelled = true;
    };
  }, [online]);

  if (!VISITOR_STRIP_ENABLED || !online || !data) return null;
  return (
    <div
      role="status"
      className="w-full border-b border-[#FCC033] bg-[#FFF4D1] px-3 py-1 text-center text-xs font-semibold text-[#07284C] sm:text-sm"
      title="Approximate. Counted per browser, no personal data stored."
    >
      👥 <span className="tabular-nums">{data.visitors.toLocaleString("en-ZA")}</span> visitors ·{" "}
      <span className="tabular-nums">{data.views.toLocaleString("en-ZA")}</span> page views
      {sinceLabel(data.since)}
    </div>
  );
}
