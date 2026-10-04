"use client";

import { useEffect, useState } from "react";

/**
 * Balungile Ntambo, the heroine of UKUVUKA, walking to and fro while the explorer loads.
 * The art is her own eight-frame walk cycle from the game (public/balungile-walk.png, one row
 * of 58x94 frames facing right). The CSS lives in globals.css (`.ss-bal*`): the sprite steps through
 * the frames, one wrapper paces left to right and back, another flips her at each end.
 * Nothing is rendered unless `loading` is true, so the page cleans up by itself when data arrives.
 */
type Props = {
  loading: boolean;
  label?: string;
  /** Force the still pose (tests, or a caller that already knows). Default: follow the OS setting. */
  reducedMotion?: boolean;
};

const QUERY = "(prefers-reduced-motion: reduce)";

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const mq = window.matchMedia(QUERY);
    setReduced(mq.matches);
    const on = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener?.("change", on);
    return () => mq.removeEventListener?.("change", on);
  }, []);
  return reduced;
}

export function BalungileWalker({ loading, label = "Loading employers…", reducedMotion }: Props) {
  const osReduced = usePrefersReducedMotion();
  if (!loading) return null;
  const still = reducedMotion ?? osReduced;
  return (
    <div
      data-balungile
      data-motion={still ? "reduced" : "walk"}
      className="ss-bal mt-2 w-full rounded-xl border border-gold/40 bg-[#071528]/75 px-3 pb-2 pt-1 text-center shadow-lg backdrop-blur-sm"
    >
      <div aria-hidden="true" className="ss-bal-track">
        <div className="ss-bal-pace">
          <div className="ss-bal-turn">
            <div className="ss-bal-sprite" />
          </div>
        </div>
      </div>
      <div aria-hidden="true" className="ss-bal-ground" />
      <p role="status" aria-live="polite" className="mt-1.5 text-xs font-semibold text-[#ffe08a]">{label}</p>
    </div>
  );
}
