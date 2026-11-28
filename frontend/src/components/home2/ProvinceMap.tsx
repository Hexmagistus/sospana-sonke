"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { SA_PROVINCE_SHAPES, SA_VIEWBOX } from "@/data/saProvinceShapes";

export type ProvinceRow = {
  code: string;
  name: string;
  population: number;
  unemployment: number;
  opps: number;
  employers: number;
};

type Sources = { mype: string; qlfs: string; mypeUrl: string; qlfsUrl: string; oppsDate: string };

/** Soft, light fills per province (bright palette; text never sits on these). */
const FILL: Record<string, string> = {
  GP: "#F6C9B8", KZN: "#BFE3E0", WC: "#F8DFA3", EC: "#CFE8D6", LP: "#F3D4C2",
  MP: "#C9E4EC", NW: "#F7E6B8", FS: "#D8EEDC", NC: "#FBEBD0",
};
const ACTIVE = "#B8432A";

const fmtInt = (n: number) => n.toLocaleString("en-ZA").replace(/,/g, " ");

function MapSvg({
  selected,
  onPick,
  label,
  interactive,
}: {
  selected: string | null;
  onPick: (code: string) => void;
  label: string;
  interactive: boolean;
}) {
  return (
    <svg viewBox={SA_VIEWBOX} role="group" aria-label={label} className="h-auto w-full drop-shadow-[0_18px_24px_rgba(31,35,40,0.16)]">
      <defs>
        <linearGradient id="ss-map-sheen" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.55" />
          <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
        </linearGradient>
      </defs>
      {SA_PROVINCE_SHAPES.map((p) => {
        const on = selected === p.code;
        return (
          <g key={p.code}>
            <path
              d={p.d}
              fill={on ? ACTIVE : FILL[p.code]}
              stroke="#ffffff"
              strokeWidth={2.5}
              strokeLinejoin="round"
              className={interactive ? "cursor-pointer outline-none transition-[fill] duration-200 hover:brightness-95 focus-visible:brightness-90 motion-reduce:transition-none" : ""}
              role={interactive ? "button" : undefined}
              tabIndex={interactive ? 0 : -1}
              aria-label={interactive ? `${p.name}${on ? " (selected)" : ""}` : undefined}
              aria-pressed={interactive ? on : undefined}
              onClick={() => onPick(p.code)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onPick(p.code);
                }
              }}
            />
            <path d={p.d} fill="url(#ss-map-sheen)" pointerEvents="none" />
            <text
              x={p.cx}
              y={p.cy}
              textAnchor="middle"
              dominantBaseline="middle"
              pointerEvents="none"
              className="select-none text-[15px] font-bold"
              fill={on ? "#ffffff" : "#1F2328"}
            >
              {p.code}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/** Hero map: decorative but clickable; a click opens that province in the Explore section. */
export function HeroMap() {
  const [hover, setHover] = useState<string | null>(null);
  return (
    <div onMouseLeave={() => setHover(null)}>
      <MapSvg
        selected={hover}
        interactive
        label="Map of South Africa's nine provinces. Choose one to see its figures below."
        onPick={(code) => {
          setHover(code);
          window.location.hash = `province-${code}`;
        }}
      />
    </div>
  );
}

/** Explore section: clickable map with a stats panel for the chosen province. */
export function ExploreMap({ rows, sources }: { rows: ProvinceRow[]; sources: Sources }) {
  const [code, setCode] = useState<string>("GP");

  useEffect(() => {
    const read = () => {
      const m = window.location.hash.match(/^#province-([A-Z]+)$/);
      if (m && rows.some((r) => r.code === m[1])) {
        setCode(m[1]);
        document.getElementById("explore")?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
      }
    };
    read();
    window.addEventListener("hashchange", read);
    return () => window.removeEventListener("hashchange", read);
  }, [rows]);

  const row = rows.find((r) => r.code === code) ?? rows[0];

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
      <div className="rounded-3xl border border-white/70 bg-gradient-to-br from-white to-[#FFF4E2] p-4 shadow-[0_24px_48px_-28px_rgba(31,35,40,0.35)] sm:p-6">
        <MapSvg selected={code} onPick={setCode} interactive label="Choose a province" />
        <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label="Choose a province">
          {rows.map((r) => (
            <button
              key={r.code}
              type="button"
              onClick={() => setCode(r.code)}
              aria-pressed={r.code === code}
              className={`rounded-full border px-3 py-1.5 text-sm font-semibold transition-colors motion-reduce:transition-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0B6575] ${
                r.code === code ? "border-[#B8432A] bg-[#B8432A] text-white" : "border-[#1F2328]/15 bg-white text-[#1F2328] hover:border-[#B8432A]"
              }`}
            >
              {r.name}
            </button>
          ))}
        </div>
      </div>

      <div aria-live="polite" className="rounded-3xl border border-white/70 bg-white/90 p-6 shadow-[0_24px_48px_-28px_rgba(31,35,40,0.35)] backdrop-blur">
        <p className="text-sm font-semibold uppercase tracking-wide text-[#0B6575]">Province</p>
        <h3 className="mt-1 text-2xl font-extrabold tracking-tight text-[#1F2328]">{row.name}</h3>
        <dl className="mt-5 grid grid-cols-2 gap-4">
          <div className="rounded-2xl bg-[#FBF6EC] p-4">
            <dt className="text-sm font-medium text-[#4A4F57]">People</dt>
            <dd className="mt-1 text-2xl font-extrabold tabular-nums text-[#1F2328]">{(row.population / 1e6).toFixed(2)}M</dd>
            <dd className="mt-1 text-xs text-[#4A4F57]">
              <a className="underline" href={sources.mypeUrl} target="_blank" rel="noopener noreferrer">{sources.mype}</a>
            </dd>
          </div>
          <div className="rounded-2xl bg-[#FBF0EC] p-4">
            <dt className="text-sm font-medium text-[#4A4F57]">Unemployment rate</dt>
            <dd className="mt-1 text-2xl font-extrabold tabular-nums text-[#1F2328]">{row.unemployment.toFixed(1)}%</dd>
            <dd className="mt-1 text-xs text-[#4A4F57]">
              <a className="underline" href={sources.qlfsUrl} target="_blank" rel="noopener noreferrer">{sources.qlfs}</a>
            </dd>
          </div>
          <div className="rounded-2xl bg-[#EEF6F7] p-4">
            <dt className="text-sm font-medium text-[#4A4F57]">Open posts listed here</dt>
            <dd className="mt-1 text-2xl font-extrabold tabular-nums text-[#1F2328]">{fmtInt(row.opps)}</dd>
            <dd className="mt-1 text-xs text-[#4A4F57]">Sospana Sonke list, {sources.oppsDate}</dd>
          </div>
          <div className="rounded-2xl bg-[#EDF6F0] p-4">
            <dt className="text-sm font-medium text-[#4A4F57]">Employers hiring</dt>
            <dd className="mt-1 text-2xl font-extrabold tabular-nums text-[#1F2328]">{fmtInt(row.employers)}</dd>
            <dd className="mt-1 text-xs text-[#4A4F57]">with an open post in {row.name}</dd>
          </div>
        </dl>
        <p className="mt-4 text-xs leading-relaxed text-[#4A4F57]">
          Posts are counted by the location the employer gives. Posts with no location, several provinces or
          &ldquo;remote&rdquo; are not counted in any province.
        </p>
        <Link
          href={`/opportunities-today?prov=${row.code}`}
          className="mt-5 inline-flex items-center gap-2 rounded-full bg-[#B8432A] px-5 py-2.5 text-sm font-bold text-white shadow-md transition hover:-translate-y-0.5 hover:bg-[#9A3722] motion-reduce:transition-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0B6575]"
        >
          See open posts in {row.name} →
        </Link>
      </div>
    </div>
  );
}
