"use client";

import { useEffect, useState } from "react";
import { BalungileWalker } from "./BalungileWalker";

export const GUIDE_STORAGE_KEY = "ss-directory-guide";

type Props = {
  steps: readonly string[];
  /** Start state for tests / server markup. Real use reads localStorage after mount. */
  initialOpen?: boolean | null;
  /** While true, Balungile walks to and fro just below the card (see BalungileWalker). */
  loading?: boolean;
  loadingLabel?: string;
};

/**
 * Compact "How to use" card for the hero banner: always dark, readable over the photo.
 * Hide/Show is remembered in localStorage (same key as before).
 */
export function HowToUseCard({ steps, initialOpen = null, loading = false, loadingLabel }: Props) {
  const [open, setOpen] = useState<boolean | null>(initialOpen);

  useEffect(() => {
    if (initialOpen !== null) return;
    try { setOpen(localStorage.getItem(GUIDE_STORAGE_KEY) !== "hidden"); } catch { setOpen(true); }
  }, [initialOpen]);

  if (open === null) return null;

  const walker = <BalungileWalker loading={loading} label={loadingLabel} />;

  if (!open) {
    return (
      <>
      <button
        type="button"
        onClick={() => {
          setOpen(true);
          try { localStorage.removeItem(GUIDE_STORAGE_KEY); } catch { /* private mode */ }
        }}
        className="rounded-full border border-gold/60 bg-ss-panel px-3 py-1 text-xs font-semibold text-ss-primary backdrop-blur hover:bg-ss-surface"
      >
        How to use
      </button>
      {walker}
      </>
    );
  }

  return (
    <>
    <section
      aria-label="How to use"
      className="w-full rounded-xl border border-gold/50 bg-ss-panel p-3 text-ss-text shadow-lg backdrop-blur-sm"
    >
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <h2 className="text-sm font-extrabold text-ss-primary">How to use</h2>
        <button
          type="button"
          onClick={() => {
            setOpen(false);
            try { localStorage.setItem(GUIDE_STORAGE_KEY, "hidden"); } catch { /* private mode */ }
          }}
          className="rounded-full px-2 py-0.5 text-[11px] font-semibold text-ss-muted hover:bg-ss-primary-soft"
        >
          Hide
        </button>
      </div>
      <ol className="space-y-1.5">
        {steps.map((step, i) => (
          <li key={step} className="flex min-w-0 items-start gap-2 text-[13px] leading-snug text-ss-text">
            <span aria-hidden className="mt-px flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gold text-[11px] font-extrabold text-navy">
              {i + 1}
            </span>
            <span className="min-w-0">{step}</span>
          </li>
        ))}
      </ol>
    </section>
    {walker}
    </>
  );
}
