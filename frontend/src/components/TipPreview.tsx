"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Latest = { kind: string; body: string | null; author: string };
type Summary = Record<string, { total: number; works: number; broken: number; latest: Latest }>;

const ICON: Record<string, string> = { works: "✅", broken: "⚠️", open: "🕒", closed: "🔒", tip: "💡" };
const WORDS: Record<string, string> = {
  works: "Link works", broken: "Link broken", open: "Applications open", closed: "Closed", tip: "Tip",
};

// One shared fetch for every card on the page.
let cache: Promise<Summary> | null = null;
let cachedAt = 0;
function loadSummary(): Promise<Summary> {
  if (!cache || Date.now() - cachedAt > 60_000) {
    cachedAt = Date.now();
    cache = api.get<Summary>("/comments/summary").catch(() => ({} as Summary));
  }
  return cache;
}

export const OPEN_TIPS_EVENT = "ss-open-tips";

/** Latest community tip on a card, next to the View jobs button, so people see it at a glance. */
export function TipPreview({ companyId, onOpen }: { companyId: string; onOpen?: () => void }) {
  const [s, setS] = useState<Summary[string] | null>(null);
  useEffect(() => {
    let live = true;
    loadSummary().then((all) => { if (live) setS(all[companyId] || null); });
    return () => { live = false; };
  }, [companyId]);

  return (
    <button
      type="button"
      onClick={() => { onOpen?.(); window.dispatchEvent(new CustomEvent(OPEN_TIPS_EVENT, { detail: companyId })); }}
      className="min-w-0 flex-1 rounded-xl border border-dashed border-ss-border px-3 py-2 text-left transition hover:border-brand hover:bg-brand/5"
    >
      {s ? (
        <>
          <div className="flex flex-wrap items-center gap-x-2 text-[11px] font-semibold text-brand-dark">
            <span>💬 {s.total} tip{s.total === 1 ? "" : "s"}</span>
            {s.works > 0 && <span>✅ {s.works} say link works</span>}
            {s.broken > 0 && <span className="text-red-600">⚠️ {s.broken} say broken</span>}
          </div>
          <div className="mt-0.5 line-clamp-2 break-words text-xs text-ss-muted">
            {ICON[s.latest.kind]} {s.latest.body ? `“${s.latest.body}”` : WORDS[s.latest.kind]}
            <span className="text-[10px]"> · {s.latest.author}</span>
          </div>
        </>
      ) : (
        <div className="text-xs text-ss-muted">💬 No tips yet. Been here? Tap to help others decide.</div>
      )}
    </button>
  );
}
