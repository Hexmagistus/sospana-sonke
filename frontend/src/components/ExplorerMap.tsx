"use client";

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import worldMap from "@/data/world-map.json";
import { TIERS, tierOf, type TierId } from "@/lib/regions";
import {
  WORLD_VIEW, clampView, easeInOutCubic, keyAction, mixViews, panView, viewBoxString, viewForCountry,
  MAX_ZOOM_VIEW_W, wheelFactor, zoomView, type View,
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

const GOLD = "#f5b301";
const OCEAN = "var(--map-ocean)";
const LAND = "var(--map-land)";
const LAND_STROKE = "var(--map-land-stroke)";

const BTN =
  "inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg border-2 border-navy bg-ss-surface px-2 text-xl font-bold text-ss-text shadow-md hover:bg-ss-primary-soft-strong focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-navy disabled:cursor-not-allowed disabled:opacity-60";

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
  const rafRef = useRef(0);
  const stopAnimation = useCallback(() => cancelAnimationFrame(rafRef.current), []);
  const animateTo = useCallback((to: View) => {
    cancelAnimationFrame(rafRef.current);
    if (reduced) {
      setView(to);
      return;
    }
    const from = viewRef.current;
    const start = performance.now();
    const duration = 750;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      setView(mixViews(from, to, easeInOutCubic(t)));
      if (t < 1) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
  }, [reduced]);
  // Choosing a country (or clearing it) still flies the camera there.
  useEffect(() => {
    animateTo(target);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, animateTo]);

  /* ---- drag / wheel / pinch / buttons / keyboard ---- */
  // Locked = one finger scrolls the page (default on touch screens); unlocked = the map owns
  // drag, wheel and pinch. The +/- and Reset buttons and the keyboard always work.
  const [locked, setLocked] = useState(false);
  useEffect(() => {
    setLocked(window.matchMedia("(pointer: coarse)").matches);
  }, []);
  const box = useRef<HTMLDivElement>(null);
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const gesture = useRef<{ moved: boolean; pinch: number } | null>(null);
  const suppressClick = useRef(false);

  const apply = useCallback((next: View) => {
    stopAnimation();
    const v = clampView(next);
    viewRef.current = v;
    setView(v);
  }, [stopAnimation]);
  const zoomBy = useCallback((factor: number, fx = 0.5, fy = 0.5) => apply(zoomView(viewRef.current, factor, fx, fy)), [apply]);
  const resetView = useCallback(() => animateTo(target), [animateTo, target]);

  // Wheel needs a non-passive listener so it can keep the page from scrolling while zooming.
  useEffect(() => {
    const el = box.current;
    if (!el || locked) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const r = el.getBoundingClientRect();
      zoomBy(wheelFactor(e.deltaY), (e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [locked, zoomBy]);

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (locked || (e.target as Element).closest("[data-map-controls]")) return;
    if (e.pointerType === "mouse" && e.button !== 0) return;
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const pts = [...pointers.current.values()];
    gesture.current = { moved: false, pinch: pts.length === 2 ? Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y) : 0 };
  };
  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const prev = pointers.current.get(e.pointerId);
    const el = box.current;
    if (!prev || !el || !gesture.current) return;
    const r = el.getBoundingClientRect();
    const g = gesture.current;
    const cur = { x: e.clientX, y: e.clientY };
    const v = viewRef.current;
    const upp = v.w / r.width; // map units per screen pixel
    if (pointers.current.size === 1) {
      if (!g.moved && Math.hypot(cur.x - prev.x, cur.y - prev.y) < 1) return;
      if (!g.moved) {
        g.moved = true;
        suppressClick.current = true;
        el.setPointerCapture(e.pointerId);
      }
      pointers.current.set(e.pointerId, cur);
      apply(panView(v, -(cur.x - prev.x) * upp, -(cur.y - prev.y) * upp));
    } else if (pointers.current.size === 2) {
      pointers.current.set(e.pointerId, cur);
      const [a, b] = [...pointers.current.values()];
      const dist = Math.hypot(a.x - b.x, a.y - b.y);
      const mid = { x: (a.x + b.x) / 2 - r.left, y: (a.y + b.y) / 2 - r.top };
      g.moved = true;
      suppressClick.current = true;
      if (g.pinch > 0 && dist > 0) {
        apply(zoomView(v, dist / g.pinch, mid.x / r.width, mid.y / r.height));
      }
      g.pinch = dist;
    }
  };
  const onPointerEnd = (e: React.PointerEvent<HTMLDivElement>) => {
    pointers.current.delete(e.pointerId);
    if (pointers.current.size === 0) {
      gesture.current = null;
      // The click that follows a drag must not select a country.
      setTimeout(() => { suppressClick.current = false; }, 0);
    } else if (gesture.current) {
      const pts = [...pointers.current.values()];
      gesture.current.pinch = pts.length === 2 ? Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y) : 0;
    }
  };
  const onKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.target !== e.currentTarget || e.ctrlKey || e.metaKey || e.altKey) return;
    const a = keyAction(e.key);
    if (!a) return;
    e.preventDefault();
    if (a.kind === "pan") apply(panView(viewRef.current, a.dx * viewRef.current.w, a.dy * viewRef.current.h));
    else if (a.kind === "zoom") zoomBy(a.factor);
    else resetView();
  };
  const select = (name: string) => {
    if (suppressClick.current) return;
    onSelect(name);
  };

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
    <div className="ss-map relative overflow-hidden rounded-2xl border border-ss-border" style={{ background: OCEAN }}>
    <div
      ref={box}
      tabIndex={0}
      role="group"
      aria-label="Interactive world map. Drag to move, scroll or pinch to zoom. Arrow keys move, plus and minus zoom, 0 resets."
      className={`relative select-none overflow-hidden focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-[-4px] focus-visible:outline-navy ${locked ? "" : "cursor-grab active:cursor-grabbing"}`}
      style={{ touchAction: locked ? "auto" : "none" }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerEnd}
      onPointerCancel={onPointerEnd}
      onKeyDown={onKeyDown}
    >
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
            <path d="M0 28 H20 M36 28 H56 M28 0 V18 M28 38 V56 M20 28 V14 H36 M20 28 V42 H36" fill="none" style={{ stroke: "var(--map-circuit)" }} strokeWidth="0.6" />
            <circle cx="20" cy="28" r="1.2" style={{ fill: "var(--map-circuit)" }} />
            <circle cx="36" cy="28" r="1.2" style={{ fill: "var(--map-circuit)" }} />
            <circle cx="28" cy="18" r="1" style={{ fill: "var(--map-circuit)" }} />
          </pattern>
          <filter id={glowId} x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="3" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <rect x={-200} y={-200} width={1360} height={900} style={{ fill: OCEAN }} />
        <rect x={0} y={0} width={WORLD_VIEW.w} height={WORLD_VIEW.h} fill={`url(#${patternId})`} style={{ opacity: "var(--map-circuit-opacity)" }} />

        <g aria-hidden="true">
          {uncovered.map((s) => (
            <path key={s.id} d={s.d} style={{ fill: LAND, stroke: LAND_STROKE }} strokeWidth={0.6} vectorEffect="non-scaling-stroke"
              onMouseEnter={() => setHover(s.name)} />
          ))}
          {covered.filter((s) => s.name !== selected).map((s) => (
            <path
              key={s.id}
              d={s.d}
              fill={TIER_FILL[tierOf(s.name)]}
              style={{ stroke: "var(--map-covered-stroke)", fillOpacity: hover === s.name ? 0.95 : "var(--map-covered-opacity)" }}
              strokeWidth={0.8}
              vectorEffect="non-scaling-stroke"
              className="cursor-pointer"
              data-country={s.name}
              onMouseEnter={() => setHover(s.name)}
              onClick={() => select(s.name)}
            />
          ))}
          {selectedShape && (
            <path d={selectedShape.d} fill={GOLD} style={{ stroke: "var(--map-select-stroke)" }} strokeWidth={2} vectorEffect="non-scaling-stroke"
              filter={`url(#${glowId})`} data-selected="true" onClick={() => select(selectedShape.name)} />
          )}
          {selectedShape && (
            <g transform={`translate(${selectedShape.x} ${selectedShape.y}) scale(${k})`}>
              <circle r={26} fill={GOLD} opacity={0.14} className="ss-ripple" />
              <circle r={15} fill={GOLD} opacity={0.22} className="ss-ripple ss-ripple-late" />
              <circle r={7} fill={GOLD} opacity={0.35} />
              <circle r={3.4} style={{ fill: "var(--map-pin)" }} stroke={GOLD} strokeWidth={1.2} vectorEffect="non-scaling-stroke" />
            </g>
          )}
        </g>
      </svg>

      {locked && (
        <p className="pointer-events-none absolute bottom-2 right-2 max-w-[11rem] rounded-lg border border-ss-border bg-ss-surface px-2 py-1 text-xs font-semibold text-ss-text">
          Page scrolls. Unlock the map below to move it with your fingers.
        </p>
      )}
      <div aria-hidden className="pointer-events-none absolute bottom-2 left-2 rounded-lg border border-ss-border px-2.5 py-1 text-xs font-semibold text-ss-text" style={{ visibility: hover ? "visible" : "hidden", background: "var(--map-label-bg)" }}>
        {hover ?? "–"}{hover ? <span className="ml-1.5 text-ss-primary">{hoverCount > 0 ? `${hoverCount.toLocaleString()} ${noun}` : "no entries yet"}</span> : null}
      </div>
    </div>
      <div data-map-controls className="relative z-10 flex flex-wrap items-center gap-2 border-t border-ss-border bg-ss-surface p-2">
        <button type="button" onClick={() => zoomBy(1.5)} disabled={view.w <= MAX_ZOOM_VIEW_W + 0.01} aria-label="Zoom in" className={BTN}>+</button>
        <button type="button" onClick={() => zoomBy(1 / 1.5)} disabled={view.w >= WORLD_VIEW.w - 0.01} aria-label="Zoom out" className={BTN}>−</button>
        <button type="button" onClick={resetView} className={`${BTN} px-3 text-sm`}>Reset view</button>
        <button type="button" onClick={() => setLocked((l) => !l)} aria-pressed={locked} className={`${BTN} px-3 text-sm`}>
          {locked ? "🔒 Map locked: page scrolls" : "🔓 Map free: drag to move"}
        </button>
      </div>
      <p className="sr-only">{alt}</p>
    </div>
  );
}
