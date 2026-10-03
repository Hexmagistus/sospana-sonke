"use client";

import { useId, useMemo, useRef, useState, type KeyboardEvent, type MouseEvent, type PointerEvent } from "react";
import worldMap from "@/data/world-map.json";

/**
 * Natural Earth country shapes (public domain), via world-atlas 2.0.2,
 * projected once at build time. See frontend/scripts/build-world-map.mjs.
 * Antarctica is omitted so the countries stay large enough to read.
 */

export type MapCountry = { name: string; count: number; flag?: string };

type Shape = {
  id: string;
  name: string;
  d: string;
  x: number;
  y: number;
  dot?: boolean;
};

const SHAPES = worldMap.countries as Shape[];
const VB_W = worldMap.w;
const VB_H = worldMap.h;

const NAVY = "#071528";
const OCEAN = "#0b1f3a";
const UNCOVERED = "#1a3358";
const UNCOVERED_STROKE = "#2e4f7a";

/** Priority order: South Africa, the rest of SADC, the rest of Africa, then other regions. */
const TIERS = [
  { id: "south-africa", label: "South Africa", fill: "#ffe08a" },
  { id: "sadc", label: "Rest of SADC", fill: "#f5b301" },
  { id: "africa", label: "Rest of Africa", fill: "#c47d12" },
  { id: "oceania", label: "Oceania", fill: "#5fe0d0" },
  { id: "europe", label: "Europe", fill: "#8ec5ff" },
  { id: "south-america", label: "South America", fill: "#ff9e2c" },
  { id: "north-america", label: "North America", fill: "#c4b5fd" },
  { id: "asia", label: "Asia", fill: "#f0abfc" },
] as const;

type TierId = (typeof TIERS)[number]["id"];

const TIER_FILL: Record<TierId, string> = Object.fromEntries(TIERS.map((t) => [t.id, t.fill])) as Record<TierId, string>;
const TIER_RANK: Record<TierId, number> = Object.fromEntries(TIERS.map((t, i) => [t.id, i])) as Record<TierId, number>;

const SADC = new Set([
  "Angola", "Botswana", "Comoros", "DR Congo", "Eswatini", "Lesotho",
  "Madagascar", "Malawi", "Mauritius", "Mozambique", "Namibia",
  "Seychelles", "Tanzania", "Zambia", "Zimbabwe",
]);
const OCEANIA = new Set([
  "Australia", "New Zealand", "Fiji", "Papua New Guinea", "Samoa", "Tonga", "Solomon Islands", "Vanuatu",
]);
const EUROPE = new Set([
  "United Kingdom", "Germany", "France", "Netherlands", "Switzerland", "Sweden", "Denmark",
  "Finland", "Estonia", "Ireland", "Spain", "Belgium", "Italy", "Poland", "Austria",
  "Portugal", "Greece", "Czechia", "Czech Republic", "Hungary", "Romania", "Norway", "Ukraine",
  "Luxembourg", "Malta", "Cyprus", "Latvia", "Lithuania", "Iceland", "Slovakia", "Slovenia",
  "Bulgaria", "Croatia", "Serbia", "Albania", "Bosnia and Herzegovina", "North Macedonia",
  "Montenegro", "Kosovo", "Moldova", "Belarus",
]);
const SOUTH_AMERICA = new Set([
  "Argentina", "Bolivia", "Brazil", "Chile", "Colombia", "Ecuador", "Guyana",
  "Paraguay", "Peru", "Suriname", "Uruguay", "Venezuela",
]);
const NORTH_AMERICA = new Set([
  "Canada", "United States", "United States of America", "Mexico", "Greenland",
  "Guatemala", "Belize", "Honduras", "El Salvador", "Nicaragua", "Costa Rica", "Panama",
  "Cuba", "Jamaica", "Haiti", "Dominican Republic", "Bahamas", "The Bahamas",
  "Trinidad and Tobago", "Barbados", "Puerto Rico",
]);
// Russia is shaded with Asia: most of the country is on that continent.
const ASIA = new Set([
  "India", "China", "Indonesia", "Iran", "United Arab Emirates", "Russia",
  "Japan", "South Korea", "North Korea", "Thailand", "Vietnam", "Malaysia", "Singapore",
  "Philippines", "Pakistan", "Bangladesh", "Sri Lanka", "Nepal", "Myanmar",
  "Saudi Arabia", "Qatar", "Kuwait", "Oman", "Yemen", "Iraq", "Israel", "Jordan",
  "Lebanon", "Syria", "Turkey", "Kazakhstan", "Uzbekistan", "Turkmenistan",
  "Kyrgyzstan", "Tajikistan", "Afghanistan", "Mongolia", "Taiwan", "Cambodia", "Laos",
]);

export function tierOf(name: string): TierId {
  if (name === "South Africa") return "south-africa";
  if (SADC.has(name)) return "sadc";
  if (OCEANIA.has(name)) return "oceania";
  if (EUROPE.has(name)) return "europe";
  if (SOUTH_AMERICA.has(name)) return "south-america";
  if (NORTH_AMERICA.has(name)) return "north-america";
  if (ASIA.has(name)) return "asia";
  return "africa";
}

function employerHref(name: string) {
  return `/companies?country=${encodeURIComponent(name)}`;
}

function employerLabel(count: number) {
  return `${count.toLocaleString()} ${count === 1 ? "employer" : "employers"}`;
}

type Tip = {
  key: string;
  name: string;
  count: number | null;
  left: number;
  top: number;
  source: "pointer" | "focus";
};

export default function CoverageWorldMap({ countries }: { countries: MapCountry[] }) {
  const patternId = `circuit-${useId().replace(/:/g, "")}`;
  const frameRef = useRef<HTMLDivElement | null>(null);
  const pointerKind = useRef("mouse");
  const armedTouch = useRef<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [tip, setTip] = useState<Tip | null>(null);

  const covered = useMemo(() => {
    const map = new Map<string, MapCountry>();
    for (const country of countries) {
      if (country.count > 0) map.set(country.name, country);
    }
    return map;
  }, [countries]);

  const focusShapes = useMemo(() => {
    return SHAPES.filter((shape) => covered.has(shape.name)).sort((a, b) => {
      const tier = TIER_RANK[tierOf(a.name)] - TIER_RANK[tierOf(b.name)];
      return tier || a.name.localeCompare(b.name);
    });
  }, [covered]);

  const tabId = activeId && focusShapes.some((shape) => shape.id === activeId)
    ? activeId
    : focusShapes[0]?.id ?? null;

  const paintShapes = useMemo(() => {
    const uncovered = SHAPES.filter((shape) => !covered.has(shape.name));
    const highlighted = SHAPES.filter((shape) => covered.has(shape.name)).sort((a, b) => {
      const dot = Number(Boolean(a.dot)) - Number(Boolean(b.dot));
      if (dot) return dot;
      const tier = TIER_RANK[tierOf(a.name)] - TIER_RANK[tierOf(b.name)];
      return tier || a.name.localeCompare(b.name);
    });
    return { uncovered, highlighted };
  }, [covered]);

  const tierSummary = useMemo(() => {
    const totals = new Map<TierId, { countries: number; employers: number }>();
    for (const tier of TIERS) totals.set(tier.id, { countries: 0, employers: 0 });
    for (const country of covered.values()) {
      const row = totals.get(tierOf(country.name))!;
      row.countries += 1;
      row.employers += country.count;
    }
    return totals;
  }, [covered]);

  const grouped = useMemo(() => {
    return TIERS.map((tier) => ({
      ...tier,
      rows: [...covered.values()]
        .filter((country) => tierOf(country.name) === tier.id)
        .sort((a, b) => a.name.localeCompare(b.name)),
    })).filter((tier) => tier.rows.length > 0);
  }, [covered]);

  function showTip(shape: Shape, source: Tip["source"], at?: { left: number; top: number }) {
    const row = covered.get(shape.name);
    setTip({
      key: shape.id,
      name: shape.name,
      count: row ? row.count : null,
      left: at?.left ?? (shape.x / VB_W) * 100,
      top: at?.top ?? (shape.y / VB_H) * 100,
      source,
    });
  }

  function pointerPercent(event: MouseEvent | PointerEvent) {
    const frame = frameRef.current;
    if (!frame) return { left: 50, top: 50 };
    const rect = frame.getBoundingClientRect();
    return {
      left: ((event.clientX - rect.left) / rect.width) * 100,
      top: ((event.clientY - rect.top) / rect.height) * 100,
    };
  }

  function moveFocus(event: KeyboardEvent<SVGSVGElement | HTMLAnchorElement>, current: string) {
    const keys = ["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp", "Home", "End"];
    if (!keys.includes(event.key) || focusShapes.length === 0) return;
    event.preventDefault();
    let index = focusShapes.findIndex((shape) => shape.id === current);
    if (index < 0) index = 0;
    if (event.key === "Home") index = 0;
    else if (event.key === "End") index = focusShapes.length - 1;
    else if (event.key === "ArrowRight" || event.key === "ArrowDown") index = (index + 1) % focusShapes.length;
    else index = (index - 1 + focusShapes.length) % focusShapes.length;
    const next = focusShapes[index];
    setActiveId(next.id);
    showTip(next, "focus");
    requestAnimationFrame(() => {
      document.getElementById(`world-country-${next.id}`)?.focus();
    });
  }

  function onCountryClick(event: MouseEvent<HTMLAnchorElement>, shape: Shape) {
    if (pointerKind.current === "touch" && armedTouch.current !== shape.id) {
      event.preventDefault();
      armedTouch.current = shape.id;
      setActiveId(shape.id);
      showTip(shape, "pointer", { left: (shape.x / VB_W) * 100, top: (shape.y / VB_H) * 100 });
    } else {
      armedTouch.current = null;
    }
  }

  const tipAbove = (tip?.top ?? 0) > 24;
  const tipShift = (tip?.left ?? 0) > 72 ? "-88%" : (tip?.left ?? 0) < 18 ? "-8%" : "-30%";

  return (
    <div id="coverage-world-map" className="w-full min-w-0">
      <h2 id="coverage-map-heading" className="font-display text-xl font-extrabold text-white sm:text-2xl">
        Where we list employers
      </h2>
      <p className="mt-1 max-w-3xl text-sm leading-relaxed text-blue-100">
        Real country borders. Gold marks South Africa, then the rest of SADC, then the rest of Africa.
        Other colours mark Oceania, Europe, South America, North America and Asia.
        Choosing a country opens its employer list. Sign in if you are not already.
      </p>

      <div
        ref={frameRef}
        className="relative mt-4 overflow-hidden rounded-2xl border border-white/15 shadow-2xl"
        style={{ background: OCEAN }}
      >
        <svg
          viewBox={`0 0 ${VB_W} ${VB_H}`}
          className="block h-auto w-full touch-manipulation"
          role="group"
          aria-label="World map of countries with employers. Highlighted countries are in the directory. Use the arrow keys to move between them, then Enter to open that country's employer list."
          onMouseLeave={() => {
            setTip((current) => (current?.source === "pointer" ? null : current));
          }}
        >
          <defs>
            <pattern id={patternId} width="56" height="56" patternUnits="userSpaceOnUse">
              <path
                d="M0 28 H20 M36 28 H56 M28 0 V18 M28 38 V56 M20 28 V14 H36 M20 28 V42 H36"
                fill="none"
                stroke="#f5b301"
                strokeWidth="0.7"
              />
              <circle cx="20" cy="28" r="1.3" fill="#f5b301" />
              <circle cx="36" cy="28" r="1.3" fill="#ffe08a" />
              <circle cx="28" cy="18" r="1.1" fill="#f5b301" />
            </pattern>
          </defs>
          <rect width={VB_W} height={VB_H} fill={NAVY} />
          <rect width={VB_W} height={VB_H} fill={`url(#${patternId})`} opacity="0.45" />

          {paintShapes.uncovered.map((shape) => (
            <path
              key={shape.id}
              d={shape.d}
              fill={UNCOVERED}
              stroke={UNCOVERED_STROKE}
              strokeWidth={0.45}
              aria-hidden="true"
              className="cursor-default"
              onMouseEnter={(event) => showTip(shape, "pointer", pointerPercent(event))}
              onMouseMove={(event) => showTip(shape, "pointer", pointerPercent(event))}
            />
          ))}

          {paintShapes.highlighted.map((shape) => {
            const row = covered.get(shape.name)!;
            const tier = tierOf(shape.name);
            const fill = TIER_FILL[tier];
            const label = `${shape.name}, ${employerLabel(row.count)}. Open the employer list.`;
            return (
              <a
                key={shape.id}
                id={`world-country-${shape.id}`}
                href={employerHref(shape.name)}
                aria-label={label}
                tabIndex={shape.id === tabId ? 0 : -1}
                onFocus={() => {
                  setActiveId(shape.id);
                  showTip(shape, "focus");
                }}
                onBlur={(event) => {
                  const next = event.relatedTarget as Node | null;
                  if (!frameRef.current?.contains(next)) {
                    setTip((current) => (current?.source === "focus" ? null : current));
                  }
                }}
                onKeyDown={(event) => moveFocus(event, shape.id)}
                onPointerDown={(event) => {
                  pointerKind.current = event.pointerType;
                }}
                onClick={(event) => onCountryClick(event, shape)}
                onMouseEnter={(event) => showTip(shape, "pointer", pointerPercent(event))}
                onMouseMove={(event) => showTip(shape, "pointer", pointerPercent(event))}
              >
                <path
                  d={shape.d}
                  fill={fill}
                  stroke={tip?.key === shape.id ? "#fff8e1" : "#071528"}
                  strokeWidth={tip?.key === shape.id ? 1.6 : 0.55}
                  className="cursor-pointer"
                />
                {shape.dot && (
                  <>
                    <circle cx={shape.x} cy={shape.y} r={4.6} fill={fill} stroke="#fff8e1" strokeWidth={0.7} />
                    <circle cx={shape.x} cy={shape.y} r={1.6} fill="#071528" />
                  </>
                )}
              </a>
            );
          })}
        </svg>

        {tip && (
          <div
            role="tooltip"
            className="pointer-events-none absolute z-20 max-w-[14rem] rounded-xl border border-[#f5b301]/70 bg-[#071528]/95 px-3 py-2 text-left shadow-xl"
            style={{
              left: `${tip.left}%`,
              top: `${tip.top}%`,
              transform: tipAbove
                ? `translate(${tipShift}, calc(-100% - 10px))`
                : `translate(${tipShift}, 12px)`,
            }}
          >
            <div className="text-sm font-bold text-white">{tip.name}</div>
            <div className="text-xs font-semibold text-[#ffe08a]">
              {tip.count == null ? "No employers listed" : employerLabel(tip.count)}
            </div>
          </div>
        )}
      </div>

      <ul className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 sm:grid-cols-4" aria-label="Map legend">
        {TIERS.map((tier) => {
          const summary = tierSummary.get(tier.id)!;
          const empty = summary.countries === 0;
          return (
            <li key={tier.id} className="flex min-w-0 items-start gap-2 text-xs text-blue-100">
              <span
                className="mt-0.5 h-3 w-3 shrink-0 rounded-sm border border-white/40"
                style={{ background: empty ? UNCOVERED : tier.fill }}
                aria-hidden="true"
              />
              <span className="min-w-0 leading-snug">
                <span className="block font-semibold text-white">{tier.label}</span>
                <span className="block text-blue-200">{empty ? "None yet" : employerLabel(summary.employers)}</span>
              </span>
            </li>
          );
        })}
      </ul>

      <p className="mt-3 text-[11px] leading-relaxed text-blue-200">
        Hover or focus a highlighted country to see its name and employer count.
        On a phone, tap once to read it and again to open the list. Arrow keys move between highlighted countries.
        Small islands are marked with a dot.
      </p>

      <h3 className="mt-4 text-xs font-semibold uppercase tracking-wider text-blue-200">
        Country list
      </h3>
      <nav
        aria-label="Countries with employers"
        className="mt-2 max-h-56 overflow-y-auto rounded-xl border border-white/10 bg-black/25 p-3"
      >
        {grouped.map((tier) => (
          <div key={tier.id} className="mb-3 last:mb-0">
            <p className="mb-1 flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-blue-200">
              <span className="h-2 w-2 rounded-sm" style={{ background: tier.fill }} aria-hidden="true" />
              {tier.label}
            </p>
            <ul className="grid gap-1 sm:grid-cols-2 lg:grid-cols-3">
              {tier.rows.map((country) => (
                <li key={country.name}>
                  <a
                    href={employerHref(country.name)}
                    className="flex items-baseline justify-between gap-2 rounded-lg px-2 py-1 text-sm text-white hover:bg-white/10"
                    style={{ boxShadow: `inset 2px 0 0 ${tier.fill}` }}
                  >
                    <span className="min-w-0 truncate">
                      {country.flag ? <span aria-hidden="true">{country.flag} </span> : null}
                      {country.name}
                    </span>
                    <span className="shrink-0 text-xs font-semibold text-[#ffe08a]">{country.count.toLocaleString()}</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
      <p className="mt-2 text-[10px] text-blue-300">
        Country shapes from Natural Earth, public domain. Antarctica is left off so the other countries stay readable.
      </p>
    </div>
  );
}
