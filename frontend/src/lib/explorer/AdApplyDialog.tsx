"use client";

import { useCallback, useEffect, useId, useRef } from "react";
import { api } from "@/lib/api";
import { AdApplyForm, type Receipt } from "./AdApplyForm";
import type { toPayload } from "./adSlots";

/** Modal around the form. Escape or a click on the backdrop closes it. */
export function AdApplyDialog({ slotKey, onClose }: { slotKey: string | null; onClose: () => void }) {
  const ref = useRef<HTMLDivElement | null>(null);
  const titleId = useId();
  const send = useCallback((body: ReturnType<typeof toPayload>) => api.post<Receipt>("/ads/applications", body), []);
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.querySelector<HTMLElement>("input")?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("keydown", onKey); prev?.focus?.(); };
  }, [onClose]);
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4"
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div ref={ref} role="dialog" aria-modal="true" aria-labelledby={titleId} className="my-6 w-full max-w-md rounded-2xl border border-ss-border bg-ss-surface p-5 shadow-2xl">
        <h2 id={titleId} className="mb-2 text-lg font-extrabold text-ss-text">Apply for an advertiser spot</h2>
        <AdApplyForm slotKey={slotKey} onClose={onClose} submit={send} />
      </div>
    </div>
  );
}
