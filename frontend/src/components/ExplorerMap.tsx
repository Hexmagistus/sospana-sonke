"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import worldMap from "@/data/world-map.json";
import { TIERS, tierOf, type TierId } from "@/lib/regions";
import {
  WORLD_VIEW, easeInOutCubic, mixViews, viewBoxString, viewForCountry, type View,
} from "@/lib/mapView";

/**
 * World map for the split directory view. Same Natural Earth shapes (public
 * domain) as the landing page's CoverageWorldMap, so no new data and no network.
 * The selected country glows gold with a ripple, and the camera eases to it.
 */

type Shape = { id: string; name: string; d: string; x: number; y: number; dot?: boolean };
const SHAPES = worldMap.countries as Shape[];
const BY_NAME = new Map(SHAPES.map((s) => [s.name, s]));

const TIER_FILL: Record<TierId, string> = Object.fromEntries(TIERS.map((t) => [t.id, t.fill])) as Record<TierId, string>;

const OCEAN = "#071528";
const LAND = "#13264a";
const LAND_STROKE = "#24406c";
const GOLD = "#f5b301";

export type ExplorerMapProps = {
  /** Directory countries that have employers, with their counts. */
  counts: Record<string, number>;
  /** Selected country name, or "" for the whole world. */
  selected: string;
  onSelect: (name: string) => void;
  noun?: string;
};

function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const q = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(q.matches);
    const on = () => setReduced(q.matches);
    q.addEventListener("change", on);
    return () => q.removeEventListener("change", on);
  }, []);
  return reduced;
}

export default function ExplorerMap({ counts, selected, onSelect, noun = "employers" }: ExplorerMapProps) {
  const patternId = `circuit-${useId().replace(/:/g, "")}`;
  const glowId = `glow-${useId().replace(/:/g, "")}`;
  const reduced = usePrefersReducedMotion();
  const [hover, setHover] = useState<string | null>(null);

  const selectedShape = selected ? BY_NAME.get(selected) ?? null : null;
  const target: View = useMemo(
    () => (selectedShape ? viewForCountry(selectedShape.d, selectedShape) : WORLD_VIEW),
    [selectedShape],
  );

  const [view, setView] = useState<View>(target);
  const viewRef = useRef<View>(target);
  viewRef.current = view;
  useEffect(() => {
    if (reduced) {
      setView(target);
      return;
    }
    const from = viewRef.current;
    const start = performance.now();
    const duration = 750;
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      setView(mixViews(from, target, easeInOutCubic(t)));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, reduced]);

  const { covered, uncovered } = useMemo(() => {
    const cov: Shape[] = [];
    const unc: Shape[] = [];
    for (const s of SHAPES) ((counts[s.name] ?? 0) > 0 ? cov : unc).push(s);
    return { covered: cov, uncovered: unc };
  }, [counts]);

  const k = view.w / WORLD_VIEW.w; // keeps the marker the same size on screen while zooming
  const selectedCount = selected ? counts[selected] ?? 0 : 0;
  const alt = selectedShape
    ? `World map zoomed to ${selected}, ${selectedCount.toLocaleString()} ${noun}. Gold marks the selected country. Use the country list to choose another.`
    : selected
      ? `${selected} has no outline on this map (it is too small or is not a single country). It is selected in the country list.`
      : `World map of countries with ${noun}. Use the country list to choose one.`;
  const hoverCount = hover ? counts[hover] ?? 0 : 0;

  return (
    <div className="relative overflow-hidden rounded-2xl border border-white/10" style={{ background: OCEAN }}>
      <svg
        viewBox={viewBoxString(view)}
        className="block h-auto w-full"
        role="img"
        aria-label={alt}
        preserveAspectRatio="xMidYMid slice"
        onMouseLeave={() => setHover(null)}
      >
        <defs>
          <pattern id={patternId} width="56" height="56" patternUnits="userSpaceOnUse">
            <path d="M0 28 H20 M36 28 H56 M28 0 V18 M28 38 V56 M20 28 V14 H36 M20 28 V42 H36" fill="none" stroke={GOLD} strokeWidth="0.6" />
            <circle cx="20" cy="28" r="1.2" fill={GOLD} />
            <circle cx="36" cy="28" r="1.2" fill="#ffe08a" />
            <circle cx="28" cy="18" r="1" fill={GOLD} />
          </pattern>
          <filter id={glowId} x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="3" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <rect x={-200} y={-200} width={1360} height={900} fill={OCEAN} />
        <rect x={0} y={0} width={WORLD_VIEW.w} height={WORLD_VIEW.h} fill={`url(#${patternId})`} opacity="0.22" />

        <g aria-hidden="true">
          {uncovered.map((s) => (
            <path key={s.id} d={s.d} fill={LAND} stroke={LAND_STROKE} strokeWidth={0.6} vectorEffect="non-scaling-stroke"
              onMouseEnter={() => setHover(s.name)} />
          ))}
          {covered.filter((s) => s.name !== selected).map((s) => (
            <path
              key={s.id}
              d={s.d}
              fill={TIER_FILL[tierOf(s.name)]}
              fillOpacity={hover === s.name ? 0.62 : 0.3}
              stroke="#3a5f94"
              strokeWidth={0.7}
              vectorEffect="non-scaling-stroke"
              className="cursor-pointer"
              data-country={s.name}
              onMouseEnter={() => setHover(s.name)}
              onClick={() => onSelect(s.name)}
            />
          ))}
          {selectedShape && (
            <path d={selectedShape.d} fill={GOLD} stroke="#fff8e1" strokeWidth={1.4} vectorEffect="non-scaling-stroke"
              filter={`url(#${glowId})`} data-selected="true" onClick={() => onSelect(selectedShape.name)} />
          )}
          {selectedShape && (
            <g transform={`translate(${selectedShape.x} ${selectedShape.y}) scale(${k})`}>
              <circle r={26} fill={GOLD} opacity={0.14} className="ss-ripple" />
              <circle r={15} fill={GOLD} opacity={0.22} className="ss-ripple ss-ripple-late" />
              <circle r={7} fill={GOLD} opacity={0.35} />
              <circle r={3.4} fill="#fff8e1" stroke={GOLD} strokeWidth={1.2} vectorEffect="non-scaling-stroke" />
            </g>
          )}
        </g>
      </svg>

      <div aria-hidden className="pointer-events-none absolute bottom-2 left-2 rounded-lg border border-gold/40 bg-[#071528]/90 px-2.5 py-1 text-xs font-semibold text-white" style={{ visibility: hover ? "visible" : "hidden" }}>
        {hover ?? "–"}{hover ? <span className="ml-1.5 text-[#ffe08a]">{hoverCount > 0 ? `${hoverCount.toLocaleString()} ${noun}` : "no entries yet"}</span> : null}
      </div>
      <p className="sr-only">{alt}</p>
    </div>
  );
}
