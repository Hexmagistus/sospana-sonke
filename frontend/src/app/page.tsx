"use client";

import { useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import dynamic from "next/dynamic";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { setPendingSearch } from "@/lib/agentHandoff";
import { API_BASE } from "@/lib/api";
import { HERITAGE_GROUPS, HERITAGE_SITES, type HeritageSite } from "@/data/heritageSites";
import { coverageText, tierOf, TIERS, TIER_RANK } from "@/lib/regions";
import {
  countryRows, parseStats, readCachedStats, snapshotStats, SNAPSHOT_AS_OF, writeCachedStats,
  type LandingStats,
} from "@/lib/landingStats";
import DailySparkTease from "@/components/DailySparkTease";

const CoverageWorldMap = dynamic(() => import("@/components/CoverageWorldMap"), {
  loading: () => <WorldMapSkeleton />,
});

function WorldMapSkeleton() {
  return (
    <div className="w-full" aria-hidden="true">
      <div className="h-7 w-56 rounded-lg bg-ss-surface" />
      <div className="mt-3 aspect-[960/500] w-full rounded-2xl border border-ss-border bg-[#071528] motion-safe:animate-pulse" />
      <div className="mt-3 h-40 rounded-xl bg-ss-surface" />
    </div>
  );
}

const C = {
  goldText: "#6b4700",
  // Darker twins of the brand colours for TEXT on light surfaces (>= 4.5:1 on white and cream)
  // and for fills that carry white text. Use DARK_OF[colour] rather than the bright colour.
  tealText: "#0b5e58", greenText: "#166534", skyText: "#14568f", plumText: "#5b21b6",
  sunText: "#9a3412", redText: "#b91c1c",
  navy: "#0b1f3a", ink: "#071528", gold: "#f5b301", amber: "#ff9e2c",
  teal: "#0f9d8f", mint: "#5fe0d0", red: "#e4322b", green: "#1a9e5f",
  sky: "#2f9bf6", plum: "#7c3aed", sun: "#ff7a1a", cream: "#faf6ee",
};

const DARK_OF: Record<string, string> = {
  [C.red]: C.redText, [C.sun]: C.sunText, [C.gold]: C.goldText, [C.green]: C.greenText,
  [C.teal]: C.tealText, [C.sky]: C.skyText, [C.plum]: C.plumText, [C.amber]: "#92400e", [C.mint]: C.tealText,
};
const darkOf = (c: string) => DARK_OF[c] ?? c;

/* ------------------------------------------------------------------ */
/* Motion primitives — scroll reveal, count-up, tilt, starfield, etc. */
/* ------------------------------------------------------------------ */

function useReveal<T extends HTMLElement>(threshold = 0.15) {
  const ref = useRef<T | null>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          obs.disconnect();
        }
      },
      { threshold }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, visible };
}

function Reveal({
  children,
  delay = 0,
  className = "",
  as: Tag = "div",
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
  as?: "div" | "span";
}) {
  const { ref, visible } = useReveal<HTMLDivElement>();
  return (
    <Tag
      ref={ref as never}
      className={`transition-all duration-700 ease-out ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </Tag>
  );
}

function CountUp({ target, suffix = "" }: { target: number; suffix?: string; duration?: number }) {
  // The number is the real total on first paint. A count-up that starts at 0
  // is what snapshots and no-JS readers were seeing ("0+") before the
  // animation finished. duration is accepted so older call sites still type-check.
  return <span>{target}{suffix}</span>;
}

function TiltCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement | null>(null);
  function onMove(e: React.MouseEvent<HTMLDivElement>) {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width - 0.5;
    const py = (e.clientY - r.top) / r.height - 0.5;
    el.style.transform = `perspective(900px) rotateX(${-py * 7}deg) rotateY(${px * 9}deg) translateY(-6px)`;
  }
  function onLeave() {
    const el = ref.current;
    if (!el) return;
    el.style.transform = "perspective(900px) rotateX(0deg) rotateY(0deg) translateY(0px)";
  }
  return (
    <div ref={ref} onMouseMove={onMove} onMouseLeave={onLeave} className={`transition-transform duration-200 ease-out will-change-transform ${className}`}>
      {children}
    </div>
  );
}

/* Cursor-follow glow — attaches to its immediate positioned parent. */
function CursorGlow({ color = "rgba(245,179,1,0.28)" }: { color?: string }) {
  const glowRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const el = glowRef.current?.parentElement;
    if (!el) return;
    function onMove(e: MouseEvent) {
      const rect = el!.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      if (glowRef.current) glowRef.current.style.transform = `translate(${x - 220}px, ${y - 220}px)`;
    }
    el.addEventListener("mousemove", onMove);
    return () => el.removeEventListener("mousemove", onMove);
  }, []);
  return (
    <div
      ref={glowRef}
      className="pointer-events-none absolute left-0 top-0 h-[440px] w-[440px] rounded-full blur-3xl transition-transform duration-300 ease-out"
      style={{ background: `radial-gradient(circle,${color},transparent 70%)` }}
      aria-hidden="true"
    />
  );
}

/* Faint circuit-board / network-mesh overlay. It sits behind the photographs
   and the gold/navy brand, quiet enough that the picture still reads. */
function CircuitOverlay({ className = "", opacity = 0.16 }: { className?: string; opacity?: number }) {
  const nodes: [number, number][] = [
    [30, 26], [130, 14], [220, 42], [66, 84], [182, 96], [274, 62],
    [18, 132], [116, 146], [242, 140], [322, 34], [332, 114], [78, 20],
  ];
  const edges: [number, number][] = [
    [0, 1], [1, 2], [1, 3], [3, 4], [4, 5], [3, 6], [6, 7], [7, 8],
    [2, 9], [9, 10], [4, 10], [0, 11], [11, 1],
  ];
  return (
    <svg
      className={`pointer-events-none absolute inset-0 h-full w-full ${className}`}
      viewBox="0 0 360 180"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
      style={{ opacity }}
    >
      {edges.map(([a, b], i) => (
        <line key={i} x1={nodes[a][0]} y1={nodes[a][1]} x2={nodes[b][0]} y2={nodes[b][1]} stroke="#fff" strokeWidth="0.6" />
      ))}
      {nodes.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={i % 3 === 0 ? 2.6 : 1.4} fill={i % 3 === 0 ? C.gold : "#fff"} />
      ))}
    </svg>
  );
}

/* Slow-rotating tri-colour holo-frame -- wraps a panel in a thin conic-gradient
   ring (gold → green → red, echoing the platform's palette) for a hightech,
   "powered on" edge-glow. The wrapped child supplies its own background. */
function GlowFrame({
  children,
  className = "",
  colors = [C.gold, C.green, C.red, C.sky, C.gold],
  ringClassName = "rounded-[2rem]",
}: {
  children: ReactNode;
  className?: string;
  colors?: string[];
  ringClassName?: string;
}) {
  return (
    <div className={`relative isolate overflow-hidden p-[2px] ${ringClassName} ${className}`}>
      <div
        className={`pointer-events-none absolute inset-0 motion-reduce:animate-none animate-spin-slow ${ringClassName}`}
        style={{ background: `conic-gradient(from 0deg, ${colors.join(",")})`, opacity: 0.8 }}
        aria-hidden="true"
      />
      <div className={`relative z-10 ${ringClassName}`}>{children}</div>
    </div>
  );
}

/* Southern-sky starfield with a hand-placed Southern Cross — the sky that
   actually sits over the region this platform serves. */
function Starfield({ className = "" }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let raf = 0;
    let w = 0, h = 0;
    const dpr = Math.min(2, typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1);
    const prefersReduced =
      typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

    type Star = { x: number; y: number; r: number; tw: number; phase: number };
    let stars: Star[] = [];

    function resize() {
      const rect = canvas!.getBoundingClientRect();
      w = rect.width;
      h = rect.height;
      canvas!.width = w * dpr;
      canvas!.height = h * dpr;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.min(220, Math.round((w * h) / 4200));
      stars = Array.from({ length: count }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        r: Math.random() * 1.3 + 0.3,
        tw: Math.random() * 0.02 + 0.006,
        phase: Math.random() * Math.PI * 2,
      }));
    }
    resize();
    window.addEventListener("resize", resize);

    const cross = [
      { x: 0.8, y: 0.16 },
      { x: 0.855, y: 0.34 },
      { x: 0.92, y: 0.12 },
      { x: 0.755, y: 0.24 },
    ];

    let t = 0;
    function draw() {
      ctx!.clearRect(0, 0, w, h);
      for (const s of stars) {
        const alpha = prefersReduced ? 0.55 : 0.3 + 0.55 * Math.abs(Math.sin(t * s.tw + s.phase));
        ctx!.beginPath();
        ctx!.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx!.fillStyle = `rgba(255,255,255,${alpha})`;
        ctx!.fill();
      }
      ctx!.strokeStyle = "rgba(255,255,255,0.16)";
      ctx!.lineWidth = 1;
      ctx!.beginPath();
      [[0, 1], [1, 2], [0, 3]].forEach(([a, b]) => {
        ctx!.moveTo(cross[a].x * w, cross[a].y * h);
        ctx!.lineTo(cross[b].x * w, cross[b].y * h);
      });
      ctx!.stroke();
      cross.forEach((c) => {
        ctx!.beginPath();
        ctx!.arc(c.x * w, c.y * h, 1.9, 0, Math.PI * 2);
        ctx!.fillStyle = "rgba(255,255,255,0.95)";
        ctx!.fill();
      });
      t += 1;
      if (!prefersReduced) raf = requestAnimationFrame(draw);
    }
    draw();
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);
  return <canvas ref={canvasRef} className={`pointer-events-none absolute inset-0 h-full w-full ${className}`} aria-hidden="true" />;
}

function GreetingsMarquee() {
  const items = [...GREETINGS, ...GREETINGS];
  return (
    <div
      className="relative mt-6 max-w-xl overflow-hidden"
      style={{ WebkitMaskImage: "linear-gradient(90deg,transparent,#000 10%,#000 90%,transparent)", maskImage: "linear-gradient(90deg,transparent,#000 10%,#000 90%,transparent)" }}
    >
      <div className="flex w-max gap-2 animate-marquee">
        {items.map(([word, bg], i) => (
          <span key={`${word}-${i}`} className="whitespace-nowrap rounded-full px-3 py-1 text-xs font-bold" style={{ background: "#fff", color: "#0b1220", border: `2px solid ${bg}`, boxShadow: `inset 0 -3px 0 ${bg}` }}>
            {word}
          </span>
        ))}
      </div>
    </div>
  );
}

const GREETINGS = [
  ["Sawubona", C.red], ["Molo", C.sky], ["Dumela", C.green],
  ["Lotjhani", C.gold], ["Avuxeni", C.plum], ["Ndaa", C.sun], ["Hello", C.teal],
] as const;

const VALUES = ["Ambition", "Opportunity", "Dignity", "Ubuntu", "Hustle", "Growth", "Pride", "Your future"];

// Employer counts: see src/lib/landingStats.ts. The page renders the verified
// snapshot (src/data/directory-snapshot.json) first, then swaps in the live
// numbers from the public GET /companies/stats endpoint once it answers.
type CountryCard = { name: string; flag: string; count: number };

// Cards for "Live now": the largest country in each region that has employers
// (South Africa, rest of SADC, rest of Africa, Oceania, Europe, South America,
// North America, Asia), then the next-largest countries overall. Shown in the
// standing order, biggest first inside each region.
function liveNowCards(ranked: CountryCard[], n = 12) {
  const picked: CountryCard[] = [];
  const seen = new Set<string>();
  for (const tier of TIERS) {
    const lead = ranked.find((c) => tierOf(c.name) === tier.id);
    if (lead && !seen.has(lead.name)) {
      picked.push(lead);
      seen.add(lead.name);
    }
  }
  for (const c of ranked) {
    if (picked.length >= n) break;
    if (seen.has(c.name)) continue;
    picked.push(c);
    seen.add(c.name);
  }
  return picked.sort(
    (a, b) => TIER_RANK[tierOf(a.name)] - TIER_RANK[tierOf(b.name)] || b.count - a.count || a.name.localeCompare(b.name),
  );
}

// Wonders of Africa — line-art icons drawn inline (viewBox 0 0 72 52).
const WONDERS: { name: string; place: string; art: ReactNode; photo?: string; alt?: string }[] = [
  {
    name: "Table Mountain", place: "South Africa",
    photo: "/photos/cape-town-mountain.jpg", alt: "Table Mountain above the Cape Town city bowl, seen from Signal Hill",
    art: (<><path d="M6 40 L14 24 L40 24 L46 30 L58 30 L66 40 Z" fill="none" stroke={C.gold} strokeWidth="2.5" strokeLinejoin="round" /><line x1="6" y1="40" x2="66" y2="40" stroke={C.gold} strokeWidth="2.5" /></>),
  },
  {
    name: "Victoria Falls", place: "Zim / Zambia",
    photo: "/photos/victoria-falls.jpg", alt: "Victoria Falls, on the Zimbabwe–Zambia border",
    art: (<><path d="M8 16 L64 16 L64 22 L8 22 Z" fill="none" stroke={C.mint} strokeWidth="2.5" /><g stroke={C.mint} strokeWidth="2" strokeLinecap="round"><line x1="16" y1="24" x2="16" y2="42" /><line x1="26" y1="24" x2="26" y2="44" /><line x1="36" y1="24" x2="36" y2="41" /><line x1="46" y1="24" x2="46" y2="44" /><line x1="56" y1="24" x2="56" y2="42" /></g></>),
  },
  {
    name: "Mount Kilimanjaro", place: "Tanzania",
    photo: "/photos/kilimanjaro.jpg", alt: "Mount Kilimanjaro above the clouds",
    art: (<><path d="M6 42 L30 14 L42 26 L52 18 L66 42 Z" fill="none" stroke={C.sky} strokeWidth="2.5" strokeLinejoin="round" /><path d="M24 20 L30 14 L36 20 L32 22 L28 19 Z" fill="#fff" /></>),
  },
  {
    name: "Baobab Tree", place: "Madagascar",
    photo: "/photos/baobab.jpg", alt: "Avenue of the Baobabs in Madagascar",
    art: (<><path d="M30 44 L30 26 M42 44 L42 26" stroke={C.amber} strokeWidth="3" strokeLinecap="round" /><path d="M36 26 C22 24 20 14 14 12 M36 26 C50 24 52 14 58 12 M36 26 L36 10 M36 14 C30 12 26 10 24 8 M36 14 C42 12 46 10 48 8" fill="none" stroke={C.amber} strokeWidth="2.2" strokeLinecap="round" /></>),
  },
  {
    name: "Pyramids of Giza", place: "Egypt",
    photo: "/photos/pyramids.jpg", alt: "The Pyramids of Giza",
    art: (<><path d="M8 42 L26 14 L44 42 Z" fill="none" stroke={C.gold} strokeWidth="2.5" strokeLinejoin="round" /><path d="M36 42 L50 22 L64 42 Z" fill="none" stroke={C.gold} strokeWidth="2.5" strokeLinejoin="round" /></>),
  },
  {
    name: "The Serengeti", place: "East Africa",
    photo: "/photos/serengeti.jpg", alt: "An acacia tree on the Kenyan savanna",
    art: (<><circle cx="52" cy="18" r="8" fill={C.sun} /><path d="M12 40 C20 30 26 30 34 34 C38 36 40 30 40 26 M34 34 C34 40 34 40 34 42 M40 30 C44 30 48 32 50 40 M30 34 L30 42 M22 33 L22 42" fill="none" stroke={C.gold} strokeWidth="2.2" strokeLinecap="round" /><line x1="6" y1="42" x2="66" y2="42" stroke={C.gold} strokeWidth="2.5" /></>),
  },
  {
    name: "Great Zimbabwe", place: "Zimbabwe",
    art: (<><path d="M28 44 L31 16 L41 16 L44 44 Z" fill="none" stroke={C.amber} strokeWidth="2.5" strokeLinejoin="round" /><path d="M8 44 C12 34 20 32 26 34 M46 34 C52 32 60 34 64 44" fill="none" stroke={C.amber} strokeWidth="2.2" strokeLinecap="round" /><line x1="6" y1="44" x2="66" y2="44" stroke={C.amber} strokeWidth="2.5" /></>),
  },
  {
    name: "Okavango Delta", place: "Botswana",
    photo: "/photos/okavango.jpg", alt: "Aerial view of the Okavango Delta in Botswana",
    art: (<><g stroke={C.sky} strokeWidth="2.2" fill="none" strokeLinecap="round"><path d="M8 40 C22 36 26 30 36 28 C46 26 52 20 64 14" /><path d="M36 28 C40 34 46 36 58 36" /><path d="M26 31 C28 37 30 40 30 44" /></g><path d="M14 22 C16 18 20 18 22 22 C20 24 16 24 14 22 Z" fill={C.green} /></>),
  },
  {
    name: "Namib Dunes", place: "Namibia",
    photo: "/photos/namib.jpg", alt: "Deadvlei and the dunes of Sossusvlei, Namibia",
    art: (<><circle cx="20" cy="17" r="7" fill={C.sun} /><path d="M6 44 C20 30 34 40 44 32 C54 24 62 30 66 34 L66 44 Z" fill="none" stroke={C.gold} strokeWidth="2.5" strokeLinejoin="round" /></>),
  },
  {
    name: "Lake Malawi", place: "Malawi",
    photo: "/photos/lake-malawi.jpg", alt: "Sunset over Lake Malawi",
    art: (<><g stroke={C.mint} strokeWidth="2.2" fill="none" strokeLinecap="round"><path d="M8 18 Q16 13 24 18 T40 18 T56 18 T64 18" /><path d="M8 28 Q16 23 24 28 T40 28 T56 28 T64 28" /></g><path d="M28 40 C32 36 42 36 46 40 C42 44 32 44 28 40 Z M46 40 L52 36 L52 44 Z" fill={C.sky} /></>),
  },
  {
    name: "The Nile", place: "North-East Africa",
    photo: "/photos/nile.jpg", alt: "The Nile at Murchison Falls in Uganda",
    art: (<><path d="M22 6 C36 16 12 26 30 34 C44 40 30 46 40 48" fill="none" stroke={C.sky} strokeWidth="3" strokeLinecap="round" /><g stroke={C.green} strokeWidth="2" strokeLinecap="round"><line x1="52" y1="44" x2="52" y2="30" /><line x1="57" y1="44" x2="57" y2="34" /><line x1="47" y1="44" x2="47" y2="34" /></g></>),
  },
  {
    name: "Sahara Desert", place: "North Africa",
    photo: "/photos/sahara.jpg", alt: "Sand dunes at Merzouga in the Sahara, Morocco",
    art: (<><circle cx="54" cy="14" r="6" fill={C.sun} /><path d="M40 44 L40 26" stroke={C.amber} strokeWidth="2.5" strokeLinecap="round" /><path d="M40 26 C32 22 26 22 20 26 M40 26 C48 22 54 22 60 26 M40 26 C36 20 34 16 32 12 M40 26 C44 20 46 16 48 12 M40 26 L40 13" fill="none" stroke={C.green} strokeWidth="2" strokeLinecap="round" /><path d="M6 44 C18 36 30 42 40 44 L6 44 Z" fill="none" stroke={C.gold} strokeWidth="2.2" /></>),
  },
];

// Savanna + acacia silhouette layered along the bottom of the hero.
function SavannaSilhouette() {
  return (
    <svg className="pointer-events-none absolute inset-x-0 bottom-0 w-full" height="120" viewBox="0 0 1200 120" preserveAspectRatio="none" aria-hidden="true">
      <path d="M0 120 L0 92 C160 70 320 104 480 92 C640 80 760 60 900 82 C1040 104 1120 84 1200 92 L1200 120 Z" fill="#06101f" opacity="0.55" />
      <g fill="#040c17" opacity="0.85">
        <path d="M0 120 L0 104 C200 92 360 116 560 106 C760 96 900 112 1060 104 C1120 101 1160 106 1200 104 L1200 120 Z" />
        {/* acacia tree */}
        <path d="M1030 120 L1030 78 M1030 84 C1006 82 1000 70 984 68 M1030 84 C1054 82 1060 70 1076 68 M1030 78 L1030 66" stroke="#040c17" strokeWidth="5" fill="none" strokeLinecap="round" />
        <path d="M965 70 C1005 54 1055 54 1095 70 C1075 62 985 62 965 70 Z" />
      </g>
    </svg>
  );
}

/* SOSPANA COMMAND -- the hero's futuristic search console (brief section 4/10):
   a genuine entry point into the real Career Agent search, not decoration.
   Visitors here are always anonymous (Home redirects signed-in users to
   /companies before this ever renders), so a search is queued via
   lib/agentHandoff and picked up by PendingSearchBanner once they've
   registered -- the same natural-language phrases the Career Agent's own
   quick-action buttons use, so classifyIntent parses them identically. */
function HeroSearchConsole() {
  const router = useRouter();
  const [what, setWhat] = useState("");
  const [where, setWhere] = useState("");
  const [type, setType] = useState("");

  function runSearch(e: FormEvent) {
    e.preventDefault();
    const parts: string[] = [what.trim() ? `Find jobs for ${what.trim()}` : "Find jobs I can apply for"];
    if (where.trim()) parts.push(`in ${where.trim()}`);
    if (type) parts.push(type);
    setPendingSearch(parts.join(" "));
    router.push("/register");
  }

  function runQuickCommand(phrase: string) {
    setPendingSearch(phrase);
    router.push("/register");
  }

  return (
    <div className="relative mt-8 max-w-xl rounded-2xl border border-ss-border bg-ss-surface p-4 shadow-2xl backdrop-blur-md sm:p-5">
      <div className="flex items-center justify-between">
        <span className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-widest text-ss-muted">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75" style={{ background: C.mint }} />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full" style={{ background: C.mint }} />
          </span>
          Sospana Command
        </span>
        <span className="font-mono text-[10px] tracking-wider text-ss-muted">SEARCH · LIVE</span>
      </div>

      <form onSubmit={runSearch} className="mt-3 grid gap-2 sm:grid-cols-[1.2fr_1fr_0.9fr_auto]">
        <input
          value={what}
          onChange={(e) => setWhat(e.target.value)}
          placeholder="What role? e.g. warehouse assistant"
          aria-label="What role are you looking for?"
          className="w-full rounded-xl border border-ss-border bg-ss-surface px-3.5 py-2.5 text-sm text-ss-text placeholder:text-ss-muted focus:border-navy focus:outline-none"
        />
        <input
          value={where}
          onChange={(e) => setWhere(e.target.value)}
          placeholder="Where? e.g. Gauteng"
          aria-label="Where are you looking?"
          className="w-full rounded-xl border border-ss-border bg-ss-surface px-3.5 py-2.5 text-sm text-ss-text placeholder:text-ss-muted focus:border-navy focus:outline-none"
        />
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          aria-label="Employment type"
          className="w-full rounded-xl border border-ss-border bg-ss-surface px-3 py-2.5 text-sm text-ss-text focus:border-navy focus:outline-none [&>option]:text-slate-900"
        >
          <option value="">Any type</option>
          <option value="permanent">Permanent</option>
          <option value="contract">Contract</option>
          <option value="internship">Internship</option>
          <option value="learnership">Learnership</option>
          <option value="remote">Remote</option>
        </select>
        <button
          type="submit"
          className="group relative overflow-hidden rounded-xl px-5 py-2.5 text-sm font-extrabold shadow-lg transition hover:brightness-105 hover:-translate-y-0.5"
          style={{ background: `linear-gradient(120deg,${C.gold},${C.amber})`, color: "#3a2b00" }}
        >
          Search →
        </button>
      </form>

      <div className="mt-3 flex flex-wrap gap-2">
        {[
          ["Where I can apply", "Find jobs I can apply for"],
          ["Employers in my field", "Show employers in my field I can apply to directly"],
        ].map(([label, phrase]) => (
          <button
            key={label}
            type="button"
            onClick={() => runQuickCommand(phrase)}
            className="rounded-full border border-ss-border bg-ss-surface px-3 py-1.5 text-xs font-medium text-ss-muted transition hover:border-ss-border hover:bg-ss-surface"
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [scrolled, setScrolled] = useState(false);
  // Server and first browser render both use the verified snapshot, so there is
  // no hydration mismatch; the cached or live numbers replace it after mount.
  const [stats, setStats] = useState<LandingStats>(snapshotStats);
  const RANKING_PREVIEW = 10;
  const countries = useMemo(() => countryRows(stats.byCountry), [stats]);
  const ranked = countries; // biggest first
  const liveNow = liveNowCards(ranked);
  const shownEmployers = stats.total;
  const coverage = coverageText(countries);
  const isLive = stats.source === "live";
  const mapCountries = countries;

  useEffect(() => {
    if (!loading && user) router.replace("/companies");
  }, [loading, user, router]);

  useEffect(() => {
    let cancelled = false;
    const cached = readCachedStats(window.localStorage);
    if (cached) setStats(cached);
    fetch(`${API_BASE}/companies/stats`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data: unknown) => {
        if (cancelled) return;
        // An API that predates the direct-link counts is ignored on purpose:
        // its total includes employers whose careers link is not verified yet.
        const parsed = parseStats(data);
        if (!parsed) return;
        setStats(parsed);
        writeCachedStats(window.localStorage, data);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 12);
    }
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="landing -mx-4 -my-6" style={{ background: C.cream }}>
      {/* Header */}
      <header
        className={`sticky top-0 z-50 transition-all duration-300 ${scrolled ? "border-b border-black/5 bg-[#faf6ee]/85 shadow-sm backdrop-blur-md" : ""}`}
      >
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-2 px-3 py-3 sm:px-4 sm:py-4">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="relative h-8 w-8 shrink-0 min-[360px]:h-9 min-[360px]:w-9 sm:h-10 sm:w-10">
              <div
                className="absolute inset-0 -z-10 animate-pulse-glow rounded-xl blur-md"
                style={{ background: C.gold, opacity: 0.45 }}
                aria-hidden="true"
              />
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo-mark.png" alt="" className="block h-8 w-8 max-w-none shrink-0 aspect-square rounded-xl object-cover shadow-md min-[360px]:h-9 min-[360px]:w-9 sm:h-10 sm:w-10" />
            </div>
            <span className="whitespace-nowrap font-display text-[0.85rem] font-bold tracking-tight min-[360px]:text-[0.95rem] sm:text-xl" style={{ color: C.navy }}>
              Sospana&nbsp;<span style={{ color: C.goldText }}>Sonke</span>
            </span>
          </div>
          <div className="flex shrink-0 items-center gap-1 sm:gap-2">
            <Link href="/login" className="rounded-xl px-1.5 py-2.5 text-[13px] font-semibold transition hover:bg-black/5 min-[360px]:px-2 sm:px-4 sm:text-sm" style={{ color: C.navy }}>
              Log in
            </Link>
            <Link
              href="/register"
              className="whitespace-nowrap rounded-xl px-2 py-2.5 text-[13px] font-bold text-white min-[360px]:px-2.5 shadow-sm transition hover:brightness-110 sm:px-4 sm:text-sm"
              style={{ background: C.navy }}
            >
              Get started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-4 pt-2">
        <div className="relative overflow-hidden rounded-[2rem] px-6 py-14 text-ss-text shadow-[0_24px_60px_-34px_rgba(11,36,71,0.5)] ring-1 ring-ss-border sm:px-14 sm:py-20">
          <Image
            src="/photos/cape-town-mountain.jpg"
            alt="Table Mountain above the Cape Town city bowl, seen from Signal Hill"
            fill
            priority
            sizes="(max-width: 1152px) 100vw, 1152px"
            className="object-cover object-[center_40%]"
          />
          <div
            className="absolute inset-0"
            style={{ background: "linear-gradient(105deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.88) 48%, rgba(255,255,255,0.4) 100%)" }}
          />
          <CircuitOverlay className="opacity-25" opacity={0.08} />
          <div
            className="pointer-events-none absolute inset-x-0 top-0 h-28 animate-scan-sweep"
            style={{ background: `linear-gradient(180deg, transparent, ${C.mint}2e, transparent)` }}
            aria-hidden="true"
          />
          <CursorGlow />
          {/* decorative orbs */}
          <div
            className="pointer-events-none absolute -right-16 -top-24 h-80 w-80 animate-float-slow rounded-full blur-3xl"
            style={{ background: "radial-gradient(circle at 30% 30%,#ffcf5a,#ff7a1a)", opacity: 0.22 }}
          />
          <div
            className="pointer-events-none absolute -bottom-24 -left-16 h-72 w-72 animate-float rounded-full blur-3xl"
            style={{ background: `radial-gradient(circle at 40% 40%,${C.mint},${C.teal})`, opacity: 0.16 }}
          />
          <div className="pointer-events-none absolute inset-0 bg-noise opacity-[0.05]" />
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.06]"
            style={{ backgroundImage: "radial-gradient(#fff 1px, transparent 1px)", backgroundSize: "22px 22px" }}
          />
          <div className="relative grid grid-cols-[minmax(0,1fr)] items-start gap-8 lg:grid-cols-2">
            <div className="min-w-0">
              <Reveal className="flex flex-wrap gap-2">
                <span className="inline-flex items-center gap-2 rounded-full border border-ss-border bg-ss-surface px-4 py-1.5 text-xs font-semibold backdrop-blur-sm">
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75" style={{ background: C.mint }} />
                    <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: C.mint }} />
                  </span>
                  Live across {coverage}
                </span>
                <span className="inline-flex items-center rounded-full border border-[#f5b301]/50 bg-[#f5b301]/15 px-3 py-1 text-xs font-semibold text-[#6b4700]">
                  Born in SADC, built for the world
                </span>
              </Reveal>

              <Reveal delay={80}>
                <GreetingsMarquee />
              </Reveal>

              <Reveal delay={160}>
                <h1 className="mt-6 font-display text-4xl font-extrabold leading-[1.05] tracking-tight sm:text-6xl" style={{ textShadow: "none" }}>
                  Where talent meets
                  <br />
                  <span className="animate-gradient-text bg-clip-text text-transparent" style={{ backgroundImage: `linear-gradient(90deg,#8a5a00,#b45309,#8a5a00)` }}>
                    opportunity.
                  </span>
                </h1>
              </Reveal>
              <Reveal delay={240}>
                <p className="mt-6 max-w-xl text-lg leading-relaxed text-ss-muted">
                  First made for the SADC region, now listing employers across {coverage}. Each card is a direct link to that employer&apos;s own careers page. We do not host every vacancy, and we do not promise you the job. A card that says &ldquo;Not counted yet&rdquo; does not mean the employer has no vacancies: check their careers page directly.
                </p>
              </Reveal>

              <Reveal delay={280}>
                <HeroSearchConsole />
              </Reveal>

              {/* Words to grow by */}
              <Reveal delay={320}>
                <blockquote className="mt-7 max-w-xl rounded-r-xl border-l-4 pl-4" style={{ borderColor: C.gold }}>
                  <p className="text-base italic leading-relaxed text-ss-text sm:text-lg">
                    &ldquo;Education is the most powerful weapon which you can use to change the world.&rdquo;
                  </p>
                  <footer className="mt-1.5 text-sm font-semibold" style={{ color: C.goldText }}>
                    — Nelson Mandela, former President of South Africa
                  </footer>
                </blockquote>
              </Reveal>

              <Reveal delay={400}>
                <div className="mt-8 flex flex-wrap gap-3">
                  <Link
                    href="/register"
                    className="group relative overflow-hidden rounded-xl px-6 py-3.5 font-extrabold shadow-lg transition hover:brightness-105 hover:-translate-y-0.5"
                    style={{ background: `linear-gradient(120deg,${C.gold},${C.amber})`, color: "#3a2b00" }}
                  >
                    <span className="relative z-10">Create your free account →</span>
                    <span className="pointer-events-none absolute inset-0 -translate-x-full skew-x-[-20deg] bg-white/40 opacity-0 transition-all duration-700 group-hover:translate-x-full group-hover:opacity-100" />
                  </Link>
                  <Link href="/companies" className="rounded-xl px-6 py-3.5 font-bold text-white shadow-lg transition hover:-translate-y-0.5 hover:brightness-110" style={{ background: C.navy }}>
                    Browse companies →
                  </Link>
                  <Link href="/companies?type=SOE" className="rounded-xl border border-ss-border bg-ss-surface px-6 py-3.5 font-semibold text-ss-text backdrop-blur-sm transition hover:-translate-y-0.5 hover:bg-ss-surface">
                    🏛️ State-owned employers
                  </Link>
                </div>
                <p className="mt-6 text-sm text-ss-muted">
                  <b style={{ color: C.goldText }}>Free to use</b> · Direct employer links, application tracking, and a daily agent that drafts — you still press send.
                </p>
              </Reveal>
            </div>

            <Reveal delay={200} className="w-full">
              <CoverageWorldMap countries={mapCountries} />
            </Reveal>
          </div>
        </div>
      </section>

      {/* Trust strip — HUD-style readout panel */}
      <section className="mx-auto max-w-6xl px-4">
        <Reveal delay={80}>
          <div className="relative -mt-6 overflow-hidden rounded-2xl border border-ss-border p-4 shadow-lg" style={{ background: "linear-gradient(135deg,#ffffff,#f3eee2)" }}>
            <CircuitOverlay className="opacity-40" opacity={0.14} />
            <div className="pointer-events-none absolute inset-0 bg-noise opacity-[0.04]" />
            <div className="relative grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                [shownEmployers, "", isLive ? "Employers with a direct careers link, live" : "Employers with a direct careers link", "#6b4700"],
                [null, "Direct", "To official careers pages", "#0b5e58"],
                [null, "SOE", "State-owned employers, linked", "#166534"],
                [null, "Free", "Full access, no charge", "#14568f"],
              ].map(([n, suffixOrLabel, l, col], i) => (
                <div key={l as string} className="rounded-xl border border-ss-border bg-ss-bg px-3 py-3 text-center">
                  <div
                    className="font-mono text-2xl font-extrabold tracking-tight"
                    style={{ color: col as string }}
                  >
                    {n === null ? (suffixOrLabel as string) : <CountUp target={n as number} suffix={suffixOrLabel as string} duration={1200 + i * 150} />}
                  </div>
                  <div className="mt-0.5 text-[11px] font-medium uppercase tracking-wider text-ss-muted">{l as string}</div>
                </div>
              ))}
            </div>
          </div>
        </Reveal>
      </section>

      {/* Pillars */}
      <section className="mx-auto grid max-w-6xl gap-5 px-4 py-12 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["🎯", "Straight to employers", `Direct links to ${shownEmployers.toLocaleString("en-US")} employers' official careers pages. You apply on their site. We don't invent listings.`, C.red],
          ["🏛️", "State-owned employers too", "SOEs are in the same directory, each with a link we could verify. South Africa has the most. Other countries are added the same way.", C.gold],
          ["🤖", "A daily digest, still your call", "Opt in and get one short email a day with the openings that are genuinely new. Nothing is ever sent for you.", C.sky],
          ["📈", "Track & rise", "Every application in one place. Stay organised, stay ready, and keep moving forward.", C.teal],
        ].map(([ic, t, d, col], i) => (
          <Reveal key={t as string} delay={i * 120}>
            <TiltCard>
              <div
                className="group rounded-2xl bg-white/80 p-7 shadow-[0_18px_40px_-28px_rgba(11,31,58,0.45)] ring-1 ring-black/5 backdrop-blur-md transition-shadow duration-300 hover:shadow-xl"
                style={{ borderTop: `5px solid ${col}`, boxShadow: `0 10px 34px -18px ${col}88` }}
              >
                <div
                  className="relative flex h-12 w-12 items-center justify-center rounded-xl text-2xl transition-transform group-hover:scale-110"
                  style={{ background: `${col}1a` }}
                >
                  <span className="absolute inset-0 -z-10 rounded-xl opacity-0 blur-md transition-opacity duration-300 group-hover:opacity-70" style={{ background: col }} aria-hidden="true" />
                  {ic}
                </div>
                <h3 className="mt-4 font-display text-lg font-bold" style={{ color: C.navy }}>{t}</h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-600">{d}</p>
              </div>
            </TiltCard>
          </Reveal>
        ))}
      </section>

      {/* Explore by category — futuristic directory launcher */}
      <section className="mx-auto max-w-6xl px-4 py-12">
        <Reveal className="text-center">
          <span
            className="inline-flex items-center gap-2 rounded-full border border-teal/20 bg-teal/5 px-4 py-1.5 text-xs font-bold uppercase tracking-widest"
            style={{ color: C.tealText, boxShadow: `0 0 22px ${C.mint}33` }}
          >
            ◈ Explore by category
          </span>
          <h2 className="mt-4 font-display text-2xl font-extrabold sm:text-4xl" style={{ color: C.navy }}>
            Every door to work,{" "}
            <span style={{ background: `linear-gradient(90deg,${C.tealText},${C.skyText},${C.plumText})`, WebkitBackgroundClip: "text", backgroundClip: "text", color: "transparent" }}>
              in one place
            </span>
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-gray-600">
            Tap a sector to open a live directory of employers with direct links to their official careers pages — no job boards, no dead ends.
          </p>
        </Reveal>

        <div className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-3">
          {[
            { icon: "🏢", label: "Companies", desc: "JSE-listed & private employers", href: "/companies", col: C.teal, photo: "/photos/cape-town-waterfront.jpg" },
            { icon: "🏛️", label: "State-owned", desc: "SOEs & parastatals hiring now", href: "/companies?type=SOE", col: C.plum, photo: "/photos/lagos.jpg" },
            { icon: "🎓", label: "Universities", desc: "Academic & research posts", href: "/universities", col: C.sky, photo: "/photos/marrakech.jpg" },
            { icon: "🏫", label: "Colleges", desc: "TVET & tertiary colleges", href: "/colleges", col: C.green, badge: "Featured", photo: "/photos/nairobi.jpg" },
            { icon: "🏥", label: "Hospitals", desc: "Healthcare & clinical roles", href: "/hospitals", col: C.red, photo: "/photos/cape-town-coast.jpg" },
            { icon: "🛠️", label: "SETAs & training", desc: "Skills authorities across Africa", href: "/companies?type=SETA", col: C.gold, badge: "New", photo: "/photos/team.jpg" },
          ].map((cat, i) => (
            <Reveal key={cat.label} delay={i * 80}>
              <TiltCard>
                <Link
                  href={cat.href}
                  className="group relative block overflow-hidden rounded-2xl border border-ss-border bg-ss-surface text-ss-text shadow-lg transition-all duration-300 hover:-translate-y-1 hover:shadow-xl"
                  style={{ borderTop: `5px solid ${cat.col}` }}
                >
                  <div className="relative h-24 w-full overflow-hidden">
                    <Image src={cat.photo} alt="" fill sizes="(max-width: 640px) 50vw, 30vw" className="object-cover transition duration-700 motion-safe:group-hover:scale-105" />
                    {cat.badge && (
                      <span className="absolute right-2 top-2 rounded-full bg-gold px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-navy shadow">
                        {cat.badge}
                      </span>
                    )}
                  </div>
                  <div className="relative p-4">
                    <div className="absolute -top-7 left-4 flex h-12 w-12 items-center justify-center rounded-xl border border-ss-border bg-ss-surface text-2xl shadow transition-transform duration-300 group-hover:-rotate-6 group-hover:scale-110">
                      {cat.icon}
                    </div>
                    <h3 className="mt-6 font-display text-lg font-extrabold tracking-tight text-ss-text">
                      {cat.label}
                    </h3>
                    <p className="mt-1 text-sm text-ss-muted">{cat.desc}</p>
                    <div className="mt-3 inline-flex items-center gap-1 text-sm font-bold text-navy underline-offset-2 group-hover:underline">
                      Explore <span className="transition-transform duration-300 group-hover:translate-x-1">→</span>
                    </div>
                  </div>
                </Link>
              </TiltCard>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Wonders of Africa */}
      <section className="mx-auto max-w-6xl px-4">
        <div className="relative overflow-hidden rounded-[2rem] px-6 py-12 text-ss-text shadow-xl sm:px-12" style={{ background: "linear-gradient(135deg,#ffffff,#f3eee2)" }}>
          <div className="pointer-events-none absolute inset-0 bg-noise opacity-[0.05]" />
          <CircuitOverlay className="opacity-50" opacity={0.12} />
          <div
            className="pointer-events-none absolute -left-10 -top-10 h-56 w-56 animate-float rounded-full blur-3xl"
            style={{ background: `radial-gradient(circle,${C.sun},transparent 70%)`, opacity: 0.35 }}
          />
          <Reveal className="relative text-center">
            <span className="inline-block rounded-full bg-ss-surface px-4 py-1.5 text-xs font-semibold backdrop-blur-sm">✨ Proudly African</span>
            <h2 className="mt-4 font-display text-2xl font-extrabold sm:text-4xl">The wonders of a continent behind you.</h2>
            <p className="mx-auto mt-3 max-w-2xl text-ss-muted">
              From the Cape to the Rift Valley, Africa has always built the extraordinary. Your career is the next great thing this continent creates.
            </p>
          </Reveal>
          <div className="relative mt-9 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            {WONDERS.map((w, i) => (
              <Reveal key={w.name} delay={(i % 6) * 70}>
                <TiltCard>
                  <div className="group relative h-44 overflow-hidden rounded-2xl border border-ss-border text-left shadow-lg sm:h-52">
                    {w.photo ? (
                      <Image
                        src={w.photo}
                        alt={w.alt || ""}
                        fill
                        sizes="(max-width: 640px) 50vw, 16vw"
                        className="object-cover transition duration-700 motion-safe:group-hover:scale-105"
                      />
                    ) : (
                      <div className="flex h-full flex-col items-center justify-center bg-ss-surface px-3 pt-4 backdrop-blur-sm">
                        <svg viewBox="0 0 72 52" className="h-14 w-full" aria-hidden="true">{w.art}</svg>
                      </div>
                    )}
                    <div className="absolute inset-0 bg-gradient-to-t from-[#071528]/95 via-[#071528]/25 to-transparent" />
                    <div
                      className="absolute inset-x-0 top-0 h-1 animate-shimmer opacity-80"
                      style={{ backgroundImage: `linear-gradient(90deg,${C.gold},${C.green},${C.red},${C.gold})` }}
                      aria-hidden="true"
                    />
                    <div className="absolute inset-x-0 bottom-0 bg-[#071528]/85 p-3">
                      <div className="text-sm font-bold text-white [text-shadow:0_1px_3px_rgba(0,0,0,.7)]">{w.name}</div>
                      <div className="text-xs text-white [text-shadow:0_1px_3px_rgba(0,0,0,.7)]">{w.place}</div>
                    </div>
                  </div>
                </TiltCard>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* UNESCO World Heritage Sites — Africa first, then a few from elsewhere */}
      <HeritageSection />

      {/* SADC region */}
      <section className="mx-auto max-w-6xl px-4 pt-12">
        <div className="relative overflow-hidden rounded-[2rem] px-6 py-12 text-ss-text shadow-xl sm:px-12" style={{ background: "linear-gradient(135deg,#ffffff,#f3eee2)" }}>
          <div className="pointer-events-none absolute inset-0 bg-noise opacity-[0.05]" />
          <CircuitOverlay className="opacity-45" opacity={0.12} />
          <div
            className="pointer-events-none absolute -right-10 -top-10 h-56 w-56 animate-float-slow rounded-full blur-3xl"
            style={{ background: `radial-gradient(circle,${C.gold},transparent 70%)`, opacity: 0.4 }}
          />
          <div className="relative">
            <Reveal>
              <span className="inline-block rounded-full bg-ss-surface px-4 py-1.5 text-xs font-semibold backdrop-blur-sm">🌍 Opportunity map</span>
              <h2 className="mt-4 font-display text-2xl font-extrabold sm:text-4xl">Born in SADC. Live across {coverage}.</h2>
              <p className="mt-3 max-w-3xl text-ss-muted">
                We&apos;re live across {coverage}. A country is listed once a direct careers page is verified.{" "}
                {isLive
                  ? "The counts below come from the live directory."
                  : `The counts below are from the directory on ${new Date(SNAPSHOT_AS_OF + "T12:00:00Z").toLocaleDateString("en-ZA", { day: "numeric", month: "long", year: "numeric" })}, and update as soon as the live directory answers.`}{" "}
                They count employers with a direct careers link; the full directory also lists employers whose link is still being verified.{" "}
                No testimonials, no guaranteed interviews.
              </p>
            </Reveal>

            {/* Live now */}
            <div className="mt-8">
              <p className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-ss-muted">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75" style={{ background: C.mint }} />
                  <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: C.mint }} />
                </span>
                Live now
              </p>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                {liveNow.map((c, i) => (
                  <LiveCountryCard key={c.name} c={c} i={i} />
                ))}
              </div>

              {/* A real "jump to a country" dropdown -- pick any live country,
                  its card appears right below. No long list on the page. */}
              <CountryJumpSelect live={countries} coverage={coverage} />
            </div>

            <p className="mt-5 text-sm font-semibold text-ss-muted">
              🎉 Live across {coverage} — direct careers links, one platform.
            </p>

            {/* Contribution ranking — which country is powering the most opportunities */}
            <Reveal delay={100}>
              <div className="mt-8 rounded-2xl border border-ss-border bg-ss-surface p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-ss-muted">Who&apos;s powering the directory</p>
                <p className="mt-1 text-sm text-ss-muted">Verified employers on Sospana Sonke by country — a live picture of where the region&apos;s opportunities are opening up.</p>
                <div className="mt-4 space-y-2.5">
                  {ranked.slice(0, RANKING_PREVIEW).map((c, i) => {
                    const max = ranked[0]?.count || 1;
                    const pct = Math.max(6, Math.round((c.count / max) * 100));
                    const cols = [C.gold, C.mint, C.sky, C.green, C.sun, C.plum, C.red, C.teal, C.amber, C.mint, C.sky, C.green, C.gold, C.sun, C.teal, C.plum];
                    const col = cols[i % cols.length];
                    return (
                      <BarRow key={c.name} name={c.name} flag={c.flag} pct={pct} count={c.count} color={col} delay={i * 60} />
                    );
                  })}
                </div>

                <p className="mt-3 text-[11px] text-ss-muted">
                  South Africa leads today and is listed first, then the rest of SADC, the rest of Africa and the other regions. As we verify more employers across each market, this picture will keep shifting.
                  Use the country picker above to look up any of the {countries.length} countries.
                </p>
              </div>
            </Reveal>

          </div>
        </div>
      </section>

      {/* Proud band */}
      <section className="mx-auto max-w-6xl px-4 py-12">
        <Reveal>
          <div className="rounded-3xl bg-white px-6 py-9 shadow-sm ring-1 ring-black/5 sm:px-10">
            <h2 className="font-display text-2xl font-extrabold sm:text-3xl" style={{ color: C.navy }}>Built for every young African. 🌍</h2>
            <p className="mt-3 max-w-3xl text-gray-600">
              Wherever you come from and whatever you dream in, your ambition speaks a language every employer
              understands: skill, effort, and the will to rise. One continent, one generation ready to work —
              and one platform standing behind you every step of the way.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              {VALUES.map((l, i) => {
                const cols = [C.red, C.sun, C.gold, C.green, C.teal, C.sky, C.plum];
                const col = cols[i % cols.length];
                return (
                  <span key={l} className="rounded-full px-3 py-1 text-xs font-semibold transition hover:-translate-y-0.5" style={{ background: `${col}18`, color: darkOf(col) }}>
                    {l}
                  </span>
                );
              })}
            </div>
          </div>
        </Reveal>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-6xl px-4 pb-4">
        <Reveal>
          <h2 className="text-center font-display text-2xl font-extrabold sm:text-3xl" style={{ color: C.navy }}>How it works</h2>
          <p className="mt-2 text-center text-ss-muted">Four simple steps from profile to progress.</p>
        </Reveal>
        <div className="mt-8 grid gap-5 sm:grid-cols-4">
          {[
            ["1", "Create your profile", "Add your details and upload your CV — once.", C.red],
            ["2", "Find the right openings", "Browse employers and new vacancies, and build a tailored CV + cover letter for any role you choose.", C.sun],
            ["3", "Review & approve", "Nothing is ever sent without you — review what you prepared, then apply on the employer's official page.", C.green],
            ["4", "Track & win", "Follow every application in one place.", C.sky],
          ].map(([n, t, d, col], i) => (
            <Reveal key={n as string} delay={i * 100}>
              <div
                className="group relative rounded-2xl bg-white p-6 shadow-sm ring-1 ring-black/5 transition duration-300 hover:-translate-y-1 hover:shadow-md"
                style={{ boxShadow: `0 8px 26px -16px ${col as string}80` }}
              >
                <div className="relative flex h-11 w-11 items-center justify-center rounded-xl font-display text-lg font-extrabold text-white shadow-md" style={{ background: darkOf(col as string) }}>
                  <span className="absolute -inset-1 -z-10 animate-node-pulse rounded-xl" aria-hidden="true" />
                  {n}
                </div>
                <h4 className="mt-4 font-bold" style={{ color: C.navy }}>{t}</h4>
                <p className="mt-1.5 text-sm leading-relaxed text-gray-600">{d}</p>
                <div className="mt-3 h-[3px] w-0 rounded-full transition-all duration-500 group-hover:w-full" style={{ background: col as string }} />
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <DailySparkTease />

      {/* Final CTA */}
      <section className="mx-auto max-w-6xl px-4 py-12">
        <Reveal>
          <GlowFrame colors={[C.gold, C.sky, C.mint, C.red, C.gold]}>
            <div className="relative overflow-hidden rounded-[2rem] px-6 py-14 text-center shadow-xl" style={{ background: "linear-gradient(120deg,#ffe08a,#f5b301 55%,#ffc24d)" }}>
              <div className="pointer-events-none absolute inset-0 opacity-10" style={{ backgroundImage: "radial-gradient(#000 1px, transparent 1px)", backgroundSize: "20px 20px" }} />
              <CircuitOverlay className="opacity-25 mix-blend-overlay" opacity={0.5} />
              <div className="pointer-events-none absolute -inset-1 animate-pulse-glow rounded-[2rem]" style={{ boxShadow: `0 0 90px 10px ${C.gold}66` }} />
              <div className="relative">
                <h2 className="font-display text-3xl font-extrabold sm:text-4xl" style={{ color: "#1a0f00" }}>Your ambition deserves a real platform.</h2>
                <p className="mx-auto mt-3 max-w-xl text-lg" style={{ color: "#1a0f00" }}>Build your profile, explore open vacancies, and start applying with confidence today.</p>
                <Link
                  href="/register"
                  className="group relative mt-7 inline-block overflow-hidden rounded-xl px-8 py-4 text-lg font-extrabold text-white shadow-lg transition hover:-translate-y-0.5 hover:brightness-110"
                  style={{ background: C.navy }}
                >
                  <span className="relative z-10">Get started today →</span>
                  <span className="pointer-events-none absolute inset-0 -translate-x-full skew-x-[-20deg] bg-white/25 opacity-0 transition-all duration-700 group-hover:translate-x-full group-hover:opacity-100" />
                </Link>
              </div>
            </div>
          </GlowFrame>
        </Reveal>
      </section>

      <footer className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-8 text-sm text-ss-muted">
        <span>© 2026 Sospana Sonke · Southern Africa</span>
        <div className="flex items-center gap-4">
          <Link href="/donate" className="hover:text-ss-text">Donate</Link>
          <a href="/privacy" className="hover:text-ss-text">Privacy Policy</a>
        </div>
      </footer>
    </div>
  );
}

/* One country tile in the "Live now" grid — pulled out so it can be reused for
   both the always-visible preview and the collapsible full list. */
/* UNESCO World Heritage Sites. The list and the photo credits live in
   src/data/heritageSites.ts. Sites are grouped in the standing order: South
   Africa, rest of SADC, rest of Africa, then a few from other regions. A site
   without a freely licensed photo gets a navy-and-gold card instead. */
function HeritageCard({ site, i }: { site: HeritageSite; i: number }) {
  const img = site.image;
  return (
    <li className="min-w-0">
      <Reveal delay={(i % 4) * 70} className="h-full">
      <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-ss-border bg-ss-surface shadow-lg backdrop-blur-sm">
        <div className="relative aspect-[4/3] w-full overflow-hidden">
          {img ? (
            <Image
              src={img.src}
              alt={img.alt}
              fill
              sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
              className="object-cover"
            />
          ) : (
            <div
              className="flex h-full w-full flex-col items-center justify-center gap-2 px-4 text-center"
              style={{ background: "linear-gradient(135deg,#fff7df,#ffe9a8)" }}
            >
              <CircuitOverlay className="opacity-60" opacity={0.18} />
              <svg viewBox="0 0 48 48" className="relative h-14 w-14" aria-hidden="true">
                <rect x="9" y="9" width="30" height="30" rx="3" transform="rotate(45 24 24)" fill="none" stroke="#0b2447" strokeWidth="2.5" />
                <rect x="17" y="17" width="14" height="14" rx="2" transform="rotate(45 24 24)" fill="none" stroke={C.gold} strokeWidth="1.5" opacity="0.7" />
                <circle cx="24" cy="24" r="3" fill={C.gold} />
              </svg>
              <span className="relative text-[11px] font-semibold uppercase tracking-wider text-navy">{site.place}</span>
            </div>
          )}
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/15 via-transparent to-transparent" />
          <div className="absolute inset-x-0 top-0 h-1" style={{ backgroundImage: `linear-gradient(90deg,${C.gold},${C.amber},${C.gold})` }} aria-hidden="true" />
          <span
            className="absolute right-2 top-3 rounded-full px-2.5 py-1 font-mono text-[11px] font-bold shadow"
            style={{ background: C.gold, color: C.ink }}
          >
            <span className="sr-only">Inscribed on the World Heritage List in </span>
            {site.year}
          </span>
        </div>
        <div className="flex flex-1 flex-col p-3.5">
          <h4 className="font-display text-sm font-extrabold leading-snug text-ss-text">{site.name}</h4>
          <p className="mt-0.5 text-xs font-semibold" style={{ color: C.goldText }}>{site.place}</p>
          {img && (
            <p className="mt-auto pt-2 text-[10px] leading-snug text-ss-muted">
              Photo: <a href={img.sourceUrl} target="_blank" rel="noopener noreferrer" className="underline decoration-ss-muted underline-offset-2 hover:text-ss-text">{img.author}</a>
              {" · "}
              {img.licenceUrl ? (
                <a href={img.licenceUrl} target="_blank" rel="noopener noreferrer" className="underline decoration-ss-muted underline-offset-2 hover:text-ss-text">{img.licence}</a>
              ) : (
                img.licence
              )}
              {" · Wikimedia Commons"}
            </p>
          )}
        </div>
      </div>
      </Reveal>
    </li>
  );
}

function HeritageSection() {
  let n = 0;
  return (
    <section className="mx-auto max-w-6xl px-4 pt-12" aria-labelledby="heritage-heading">
      <div className="relative overflow-hidden rounded-[2rem] px-6 py-12 text-ss-text shadow-xl sm:px-12" style={{ background: "linear-gradient(135deg,#ffffff,#f3eee2)" }}>
        <div className="pointer-events-none absolute inset-0 bg-noise opacity-[0.05]" />
        <CircuitOverlay className="opacity-50" opacity={0.12} />
        <div
          className="pointer-events-none absolute -right-10 -top-10 h-56 w-56 animate-float rounded-full blur-3xl"
          style={{ background: `radial-gradient(circle,${C.gold},transparent 70%)`, opacity: 0.35 }}
        />
        <Reveal className="relative text-center">
          <span className="inline-block rounded-full bg-ss-surface px-4 py-1.5 text-xs font-semibold backdrop-blur-sm">🏛️ UNESCO World Heritage</span>
          <h2 id="heritage-heading" className="mt-4 font-display text-2xl font-extrabold sm:text-4xl">Places the world agrees are worth keeping.</h2>
          <p className="mx-auto mt-3 max-w-2xl text-ss-muted">
            Every site below is on the UNESCO World Heritage List, with the year it was inscribed. We start at home in South Africa, move through the rest of SADC and the rest of Africa, then look at a few from the other regions our employers are in.
          </p>
        </Reveal>
        <div className="relative mt-9 space-y-10">
          {HERITAGE_GROUPS.map((group) => {
            const sites = HERITAGE_SITES.filter((x) => x.group === group.id);
            if (sites.length === 0) return null;
            return (
              <div key={group.id}>
                <h3 className="mb-4 flex items-center gap-3 text-xs font-bold uppercase tracking-wider" style={{ color: C.goldText }}>
                  <span className="h-px w-8" style={{ background: C.gold }} aria-hidden="true" />
                  {group.label}
                </h3>
                <ul className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
                  {sites.map((site) => (
                    <HeritageCard key={site.id} site={site} i={n++} />
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
        <p className="relative mt-8 text-[11px] leading-relaxed text-ss-muted">
          Names, countries and inscription years follow the{" "}
          <a href="https://whc.unesco.org/en/list/" target="_blank" rel="noopener noreferrer" className="underline underline-offset-2 hover:text-ss-text">UNESCO World Heritage List</a>
          . Sospana Sonke is not affiliated with or endorsed by UNESCO. Photos are from Wikimedia Commons under the licences shown, resized for this page; a card without a photo means we have not found a free one we can use.
        </p>
      </div>
    </section>
  );
}

function LiveCountryCard({ c, i }: { c: CountryCard; i: number }) {
  const nodeCols = [C.gold, C.mint, C.sky, C.green, C.sun, C.plum, C.red, C.teal];
  const nodeCol = nodeCols[i % nodeCols.length];
  return (
    <Reveal delay={(i % 4) * 70}>
      <div
        className="relative flex min-w-0 flex-col gap-1 rounded-2xl border border-ss-border bg-ss-surface p-3 backdrop-blur-sm transition-colors hover:border-ss-border hover:bg-white/[0.15] sm:flex-row sm:items-center sm:gap-3 sm:p-4"
        style={{ borderLeft: `3px solid ${nodeCol}` }}
      >
        <span className="text-2xl leading-none sm:text-4xl">{c.flag}</span>
        <div className="min-w-0">
          <div className="break-words text-sm font-bold leading-tight">{c.name}</div>
            <div className="mt-0.5 break-words text-xs font-semibold leading-snug" style={{ color: C.tealText }}>
            {c.count} {c.count === 1 ? "employer" : "employers"}
          </div>
          <span className="mt-1 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold" style={{ background: C.greenText, color: "#fff" }}>
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-node-pulse rounded-full bg-white/60" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-white" />
            </span>
            Live
          </span>
        </div>
      </div>
    </Reveal>
  );
}

/* A real "jump to a country" dropdown -- a native <select> (so it gets
   keyboard type-ahead and a proper mobile picker for free) listing every
   country in the directory (the same coverage line as the rest of the page)
   in the standing order (South Africa, SADC, rest of Africa, other regions). Choosing one shows just that country's card below. */
function CountryJumpSelect({ live, coverage }: { live: CountryCard[]; coverage: string }) {
  const [selected, setSelected] = useState("");
  // South Africa first, then the rest of SADC, the rest of Africa, then the
  // other regions; alphabetical inside each group (other regions grouped by region).
  const options = [...live].sort(
    (a, b) => TIER_RANK[tierOf(a.name)] - TIER_RANK[tierOf(b.name)] || a.name.localeCompare(b.name, "en"),
  );
  const chosen = options.find((o) => o.name === selected);

  return (
    <div className="mt-4">
      <label className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-ss-muted">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-node-pulse rounded-full bg-white/60" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-white" />
        </span>
        Jump to a country
      </label>
      <div className="relative w-full sm:max-w-sm">
        <select
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          className="w-full appearance-none rounded-xl border border-ss-border bg-ss-surface py-3 pl-4 pr-10 text-sm font-bold text-ss-text backdrop-blur-sm transition hover:border-ss-border hover:bg-white/20 focus:border-white/50 focus:outline-none"
        >
          <option value="" className="text-navy">Choose a country in {coverage}</option>
          {options.map((o) => (
            <option key={o.name} value={o.name} className="text-navy">
              {o.flag} {o.name} — {o.count} {o.count === 1 ? "employer" : "employers"}
            </option>
          ))}
        </select>
        <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-sm text-ss-text">▾</span>
      </div>

      {chosen && (
        <div className="mt-3 max-w-xs">
          <LiveCountryCard c={chosen} i={0} />
        </div>
      )}
    </div>
  );
}

/* Animated ranking bar — fills to its percentage only once it scrolls into view. */
function BarRow({ name, flag, pct, count, color, delay }: { name: string; flag: string; pct: number; count: number; color: string; delay: number }) {
  const { ref, visible } = useReveal<HTMLDivElement>(0.4);
  return (
    <div ref={ref} className="flex items-center gap-3">
      <div className="flex w-32 shrink-0 items-start gap-1.5 text-sm font-semibold sm:w-40">
        <span className="shrink-0">{flag}</span><span className="min-w-0 break-words leading-tight">{name}</span>
      </div>
      <div className="relative h-6 flex-1 overflow-hidden rounded-full bg-ss-surface">
        <div
          className="relative h-full overflow-hidden rounded-full transition-[width] duration-1000 ease-out"
          style={{ width: visible ? `${pct}%` : "0%", background: color, transitionDelay: `${delay}ms` }}
        >
          <div
            className="absolute inset-0 animate-shimmer"
            style={{ backgroundImage: "linear-gradient(100deg,transparent 30%,rgba(255,255,255,0.55) 50%,transparent 70%)" }}
            aria-hidden="true"
          />
        </div>
      </div>
      <div className="w-8 shrink-0 text-right text-sm font-bold tabular-nums">{count}</div>
    </div>
  );
}
