"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

const C = {
  navy: "#0b1f3a", ink: "#071528", gold: "#f5b301", amber: "#ff9e2c",
  teal: "#0f9d8f", mint: "#5fe0d0", red: "#e4322b", green: "#1a9e5f",
  sky: "#2f9bf6", plum: "#7c3aed", sun: "#ff7a1a", cream: "#faf6ee",
};

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

function CountUp({ target, duration = 1400, suffix = "" }: { target: number; duration?: number; suffix?: string }) {
  const { ref, visible } = useReveal<HTMLSpanElement>(0.6);
  // Default to the real number so SSR / no-JS / pre-hydration paints never show a
  // misleading "0" — the count-up is a bonus flourish once it scrolls into view.
  const [n, setN] = useState(target);
  useEffect(() => {
    if (!visible) return;
    setN(0);
    let raf = 0;
    const start = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setN(Math.round(target * eased));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [visible, target, duration]);
  return <span ref={ref}>{n}{suffix}</span>;
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
          <span key={`${word}-${i}`} className="whitespace-nowrap rounded-full px-3 py-1 text-xs font-bold" style={{ background: bg, color: bg === C.gold ? "#4a3600" : "#fff" }}>
            {word}
          </span>
        ))}
      </div>
    </div>
  );
}

function NdebeleStripe({ id }: { id: string }) {
  return (
    <svg className="block w-full" height={16} preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <pattern id={id} width="88" height="16" patternUnits="userSpaceOnUse">
          <rect width="88" height="16" fill="#0b0b0b" />
          <rect x="1" y="1" width="20" height="14" fill={C.red} />
          <rect x="23" y="1" width="20" height="14" fill={C.gold} />
          <rect x="45" y="1" width="20" height="14" fill={C.green} />
          <rect x="67" y="1" width="20" height="14" fill={C.sky} />
          <path d="M1 1 L11 8 L21 1 Z" fill="#0b0b0b" />
          <path d="M45 15 L55 8 L65 15 Z" fill="#0b0b0b" />
          <path d="M23 15 L33 8 L43 15 Z" fill="#fff" opacity="0.85" />
          <path d="M67 1 L77 8 L87 1 Z" fill="#fff" opacity="0.85" />
        </pattern>
      </defs>
      <rect width="100%" height="16" fill={`url(#${id})`} />
    </svg>
  );
}

// Ndebele-inspired diamond band used as a section divider.
function NdebeleDiamonds({ id }: { id: string }) {
  return (
    <svg className="block w-full" height={22} preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <pattern id={id} width="60" height="22" patternUnits="userSpaceOnUse">
          <rect width="60" height="22" fill={C.navy} />
          <path d="M15 1 L29 11 L15 21 L1 11 Z" fill={C.gold} stroke="#0b0b0b" strokeWidth="1.5" />
          <path d="M45 1 L59 11 L45 21 L31 11 Z" fill={C.red} stroke="#0b0b0b" strokeWidth="1.5" />
          <path d="M15 6 L24 11 L15 16 L6 11 Z" fill={C.green} />
          <path d="M45 6 L54 11 L45 16 L36 11 Z" fill={C.sky} />
        </pattern>
      </defs>
      <rect width="100%" height="22" fill={`url(#${id})`} />
    </svg>
  );
}

const GREETINGS = [
  ["Sawubona", C.red], ["Molo", C.sky], ["Dumela", C.green],
  ["Lotjhani", C.gold], ["Avuxeni", C.plum], ["Ndaa", C.sun], ["Hello", C.teal],
] as const;

const VALUES = ["Ambition", "Opportunity", "Dignity", "Ubuntu", "Hustle", "Growth", "Pride", "Your future"];

// Employer counts reflect the current verified directory (kept in step with the company database).
// pending = state-owned entities are live, but the country's stock-exchange listings are still being added.
const LIVE = [
  { name: "South Africa", flag: "🇿🇦", count: 767, pending: false },
  { name: "Zimbabwe", flag: "🇿🇼", count: 153, pending: false },
  { name: "Botswana", flag: "🇧🇼", count: 126, pending: false },
  { name: "Namibia", flag: "🇳🇦", count: 106, pending: false },
  { name: "Mozambique", flag: "🇲🇿", count: 91, pending: false },
  { name: "Zambia", flag: "🇿🇲", count: 82, pending: true },
  { name: "Mauritius", flag: "🇲🇺", count: 82, pending: true },
  { name: "DR Congo", flag: "🇨🇩", count: 81, pending: true },
  { name: "Lesotho", flag: "🇱🇸", count: 74, pending: false },
  { name: "Eswatini", flag: "🇸🇿", count: 72, pending: false },
  { name: "Angola", flag: "🇦🇴", count: 69, pending: true },
  { name: "Nigeria", flag: "🇳🇬", count: 68, pending: false },
  { name: "Tanzania", flag: "🇹🇿", count: 68, pending: true },
  { name: "Madagascar", flag: "🇲🇬", count: 66, pending: true },
  { name: "Malawi", flag: "🇲🇼", count: 66, pending: true },
  { name: "Côte d'Ivoire", flag: "🇨🇮", count: 62, pending: false },
  { name: "Tunisia", flag: "🇹🇳", count: 59, pending: false },
  { name: "Kenya", flag: "🇰🇪", count: 56, pending: false },
  { name: "Cameroon", flag: "🇨🇲", count: 56, pending: false },
  { name: "Egypt", flag: "🇪🇬", count: 54, pending: false },
  { name: "Togo", flag: "🇹🇬", count: 53, pending: false },
  { name: "Ethiopia", flag: "🇪🇹", count: 52, pending: false },
  { name: "Guinea", flag: "🇬🇳", count: 52, pending: false },
  { name: "Benin", flag: "🇧🇯", count: 52, pending: false },
  { name: "Ghana", flag: "🇬🇭", count: 49, pending: false },
  { name: "Uganda", flag: "🇺🇬", count: 49, pending: false },
  { name: "Gabon", flag: "🇬🇦", count: 49, pending: false },
  { name: "Sierra Leone", flag: "🇸🇱", count: 47, pending: true },
  { name: "Mali", flag: "🇲🇱", count: 46, pending: true },
  { name: "Rwanda", flag: "🇷🇼", count: 45, pending: false },
  { name: "Senegal", flag: "🇸🇳", count: 45, pending: false },
  { name: "Morocco", flag: "🇲🇦", count: 45, pending: false },
  { name: "Algeria", flag: "🇩🇿", count: 44, pending: false },
  { name: "Mauritania", flag: "🇲🇷", count: 44, pending: true },
  { name: "Niger", flag: "🇳🇪", count: 43, pending: true },
  { name: "Burkina Faso", flag: "🇧🇫", count: 41, pending: true },
  { name: "Gambia", flag: "🇬🇲", count: 38, pending: true },
  { name: "Liberia", flag: "🇱🇷", count: 35, pending: true },
  { name: "Congo", flag: "🇨🇬", count: 32, pending: true },
  { name: "Seychelles", flag: "🇸🇨", count: 31, pending: true },
  { name: "Cabo Verde", flag: "🇨🇻", count: 30, pending: true },
  { name: "Chad", flag: "🇹🇩", count: 29, pending: true },
  { name: "Guinea-Bissau", flag: "🇬🇼", count: 28, pending: true },
  { name: "Burundi", flag: "🇧🇮", count: 27, pending: true },
  { name: "Libya", flag: "🇱🇾", count: 27, pending: true },
  { name: "Comoros", flag: "🇰🇲", count: 26, pending: true },
  { name: "Djibouti", flag: "🇩🇯", count: 23, pending: true },
  { name: "Somalia", flag: "🇸🇴", count: 20, pending: true },
  { name: "Sao Tome and Principe", flag: "🇸🇹", count: 19, pending: true },
  { name: "South Sudan", flag: "🇸🇸", count: 16, pending: true },
  { name: "Sudan", flag: "🇸🇩", count: 15, pending: true },
  { name: "Central African Republic", flag: "🇨🇫", count: 15, pending: true },
  { name: "Equatorial Guinea", flag: "🇬🇶", count: 10, pending: true },
  { name: "Eritrea", flag: "🇪🇷", count: 4, pending: true },
];
const SOON: { name: string; flag: string }[] = [];

// Wonders of Africa — line-art icons drawn inline (viewBox 0 0 72 52).
const WONDERS: { name: string; place: string; art: ReactNode }[] = [
  {
    name: "Table Mountain", place: "South Africa",
    art: (<><path d="M6 40 L14 24 L40 24 L46 30 L58 30 L66 40 Z" fill="none" stroke={C.gold} strokeWidth="2.5" strokeLinejoin="round" /><line x1="6" y1="40" x2="66" y2="40" stroke={C.gold} strokeWidth="2.5" /></>),
  },
  {
    name: "Victoria Falls", place: "Zim / Zambia",
    art: (<><path d="M8 16 L64 16 L64 22 L8 22 Z" fill="none" stroke={C.mint} strokeWidth="2.5" /><g stroke={C.mint} strokeWidth="2" strokeLinecap="round"><line x1="16" y1="24" x2="16" y2="42" /><line x1="26" y1="24" x2="26" y2="44" /><line x1="36" y1="24" x2="36" y2="41" /><line x1="46" y1="24" x2="46" y2="44" /><line x1="56" y1="24" x2="56" y2="42" /></g></>),
  },
  {
    name: "Mount Kilimanjaro", place: "Tanzania",
    art: (<><path d="M6 42 L30 14 L42 26 L52 18 L66 42 Z" fill="none" stroke={C.sky} strokeWidth="2.5" strokeLinejoin="round" /><path d="M24 20 L30 14 L36 20 L32 22 L28 19 Z" fill="#fff" /></>),
  },
  {
    name: "Baobab Tree", place: "Savanna",
    art: (<><path d="M30 44 L30 26 M42 44 L42 26" stroke={C.amber} strokeWidth="3" strokeLinecap="round" /><path d="M36 26 C22 24 20 14 14 12 M36 26 C50 24 52 14 58 12 M36 26 L36 10 M36 14 C30 12 26 10 24 8 M36 14 C42 12 46 10 48 8" fill="none" stroke={C.amber} strokeWidth="2.2" strokeLinecap="round" /></>),
  },
  {
    name: "Pyramids of Giza", place: "Egypt",
    art: (<><path d="M8 42 L26 14 L44 42 Z" fill="none" stroke={C.gold} strokeWidth="2.5" strokeLinejoin="round" /><path d="M36 42 L50 22 L64 42 Z" fill="none" stroke={C.gold} strokeWidth="2.5" strokeLinejoin="round" /></>),
  },
  {
    name: "The Serengeti", place: "East Africa",
    art: (<><circle cx="52" cy="18" r="8" fill={C.sun} /><path d="M12 40 C20 30 26 30 34 34 C38 36 40 30 40 26 M34 34 C34 40 34 40 34 42 M40 30 C44 30 48 32 50 40 M30 34 L30 42 M22 33 L22 42" fill="none" stroke={C.gold} strokeWidth="2.2" strokeLinecap="round" /><line x1="6" y1="42" x2="66" y2="42" stroke={C.gold} strokeWidth="2.5" /></>),
  },
  {
    name: "Great Zimbabwe", place: "Zimbabwe",
    art: (<><path d="M28 44 L31 16 L41 16 L44 44 Z" fill="none" stroke={C.amber} strokeWidth="2.5" strokeLinejoin="round" /><path d="M8 44 C12 34 20 32 26 34 M46 34 C52 32 60 34 64 44" fill="none" stroke={C.amber} strokeWidth="2.2" strokeLinecap="round" /><line x1="6" y1="44" x2="66" y2="44" stroke={C.amber} strokeWidth="2.5" /></>),
  },
  {
    name: "Okavango Delta", place: "Botswana",
    art: (<><g stroke={C.sky} strokeWidth="2.2" fill="none" strokeLinecap="round"><path d="M8 40 C22 36 26 30 36 28 C46 26 52 20 64 14" /><path d="M36 28 C40 34 46 36 58 36" /><path d="M26 31 C28 37 30 40 30 44" /></g><path d="M14 22 C16 18 20 18 22 22 C20 24 16 24 14 22 Z" fill={C.green} /></>),
  },
  {
    name: "Namib Dunes", place: "Namibia",
    art: (<><circle cx="20" cy="17" r="7" fill={C.sun} /><path d="M6 44 C20 30 34 40 44 32 C54 24 62 30 66 34 L66 44 Z" fill="none" stroke={C.gold} strokeWidth="2.5" strokeLinejoin="round" /></>),
  },
  {
    name: "Lake Malawi", place: "Malawi",
    art: (<><g stroke={C.mint} strokeWidth="2.2" fill="none" strokeLinecap="round"><path d="M8 18 Q16 13 24 18 T40 18 T56 18 T64 18" /><path d="M8 28 Q16 23 24 28 T40 28 T56 28 T64 28" /></g><path d="M28 40 C32 36 42 36 46 40 C42 44 32 44 28 40 Z M46 40 L52 36 L52 44 Z" fill={C.sky} /></>),
  },
  {
    name: "The Nile", place: "North-East Africa",
    art: (<><path d="M22 6 C36 16 12 26 30 34 C44 40 30 46 40 48" fill="none" stroke={C.sky} strokeWidth="3" strokeLinecap="round" /><g stroke={C.green} strokeWidth="2" strokeLinecap="round"><line x1="52" y1="44" x2="52" y2="30" /><line x1="57" y1="44" x2="57" y2="34" /><line x1="47" y1="44" x2="47" y2="34" /></g></>),
  },
  {
    name: "Sahara Desert", place: "North Africa",
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

// Freehand, stylised Africa continent outline (decorative — not a precise map).
const AFRICA_PATH =
  "M148 6 C172 4 198 10 214 26 C226 38 222 52 232 62 C246 76 268 82 274 100 " +
  "C280 118 268 130 254 136 C244 140 238 150 246 162 C254 174 250 190 236 198 " +
  "C226 204 222 216 228 230 C234 244 226 258 210 262 C200 265 196 276 200 288 " +
  "C204 302 194 316 178 326 C168 332 160 330 156 318 C152 306 142 300 132 292 " +
  "C118 280 110 264 112 246 C114 230 104 220 90 214 C74 207 64 194 66 176 " +
  "C68 160 56 150 48 136 C40 122 44 106 58 98 C68 92 68 80 60 70 " +
  "C52 58 58 44 72 36 C86 28 84 16 100 10 C116 4 132 8 148 6 Z";
const MADAGASCAR_PATH =
  "M250 250 C258 246 264 254 262 268 C260 282 252 292 246 286 C240 280 244 256 250 250 Z";

// Africa rendered as a mosaic of the continent's own flags, echoing the brand mark.
function AfricaMosaic() {
  const spots: { flag: string; x: number; y: number }[] = [
    { flag: "🇲🇦", x: 92, y: 42 }, { flag: "🇩🇿", x: 128, y: 50 }, { flag: "🇪🇬", x: 208, y: 66 },
    { flag: "🇸🇩", x: 190, y: 108 }, { flag: "🇳🇬", x: 90, y: 168 }, { flag: "🇪🇹", x: 244, y: 118 },
    { flag: "🇰🇪", x: 230, y: 158 }, { flag: "🇹🇿", x: 220, y: 190 }, { flag: "🇨🇩", x: 168, y: 200 },
    { flag: "🇬🇭", x: 74, y: 190 }, { flag: "🇦🇴", x: 138, y: 240 }, { flag: "🇿🇦", x: 174, y: 300 },
  ];
  return (
    <svg viewBox="0 0 300 340" width="280" height="320" aria-hidden="true">
      <defs>
        <pattern id="africa-mosaic" width="26" height="26" patternUnits="userSpaceOnUse" patternTransform="rotate(18)">
          <rect width="26" height="26" fill={C.green} />
          <rect width="13" height="26" fill={C.gold} />
          <rect x="13" width="7" height="13" fill={C.red} />
        </pattern>
        <filter id="africa-glow" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="5" />
        </filter>
      </defs>
      <path d={AFRICA_PATH} fill="none" stroke={C.gold} strokeWidth="10" opacity="0.55" filter="url(#africa-glow)" />
      <path d={MADAGASCAR_PATH} fill="none" stroke={C.gold} strokeWidth="6" opacity="0.5" filter="url(#africa-glow)" />
      <path d={AFRICA_PATH} fill="url(#africa-mosaic)" stroke={C.gold} strokeWidth="2.5" />
      <path d={AFRICA_PATH} fill="#000" opacity="0.16" />
      <path d={MADAGASCAR_PATH} fill="url(#africa-mosaic)" stroke={C.gold} strokeWidth="1.75" />
      {spots.map((s, i) => (
        <g key={s.flag} className="animate-float-slow" style={{ animationDelay: `${i * 0.25}s` }}>
          <circle cx={s.x} cy={s.y} r="14" fill={C.navy} stroke="#fff" strokeWidth="2" />
          <text x={s.x} y={s.y + 5} fontSize="15" textAnchor="middle">{s.flag}</text>
        </g>
      ))}
    </svg>
  );
}

const FEATURES: { kind: "search" | "cap" | "support" | "grow"; title: string; sub: string }[] = [
  { kind: "search", title: "Find Jobs", sub: "Across Africa" },
  { kind: "cap", title: "Build Skills", sub: "For a Brighter Future" },
  { kind: "support", title: "Access Support", sub: "When You Need It" },
  { kind: "grow", title: "Grow Together", sub: "Stronger Communities" },
];

function FeatureIcon({ kind }: { kind: "search" | "cap" | "support" | "grow" }) {
  const common = { fill: "none", stroke: C.gold, strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  return (
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl" style={{ background: `${C.gold}1f` }}>
      <svg viewBox="0 0 24 24" width="19" height="19" aria-hidden="true">
        {kind === "search" && (<><circle cx="10.5" cy="10.5" r="6.5" {...common} /><line x1="21" y1="21" x2="15.2" y2="15.2" {...common} /></>)}
        {kind === "cap" && (<><path d="M12 4 L22 9 L12 14 L2 9 Z" {...common} /><path d="M6 11.5 V17 C6 18.5 8.5 20 12 20 C15.5 20 18 18.5 18 17 V11.5" {...common} /><line x1="22" y1="9" x2="22" y2="15" {...common} /></>)}
        {kind === "support" && (<><circle cx="9" cy="8" r="3.2" {...common} /><path d="M2.5 20 C2.5 15.5 5.5 13 9 13 C12.5 13 15.5 15.5 15.5 20" {...common} /><circle cx="17.5" cy="9" r="2.6" {...common} /><path d="M15.5 20 C15.5 16.6 17 14.6 19.2 14 C20.8 14.6 21.8 16.5 21.8 19" {...common} /></>)}
        {kind === "grow" && (<><polyline points="3,17 9,11 13,15 21,6" {...common} /><polyline points="14,6 21,6 21,13" {...common} /></>)}
      </svg>
    </span>
  );
}

// Dark ribbon of every live country's flag, closing out the hero card — the whole continent, at a glance.
function FlagRibbon() {
  const flags = [...LIVE].sort((a, b) => a.name.localeCompare(b.name));
  return (
    <div className="relative overflow-hidden rounded-b-[2rem] px-4 py-6 shadow-xl sm:px-8" style={{ background: C.ink }}>
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px" style={{ background: `${C.gold}40` }} />
      <div className="flex flex-wrap justify-center gap-x-5 gap-y-4">
        {flags.map((c) => (
          <div key={c.name} className="flex w-16 flex-col items-center gap-1 text-center">
            <span className="text-2xl leading-none">{c.flag}</span>
            <span className="text-[10px] font-medium leading-tight text-blue-200">{c.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/companies");
  }, [loading, user, router]);

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
      <NdebeleStripe id="nd-top" />

      {/* Header */}
      <header
        className={`sticky top-0 z-50 transition-all duration-300 ${scrolled ? "border-b border-black/5 bg-[#faf6ee]/85 shadow-sm backdrop-blur-md" : ""}`}
      >
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo-mark.png" alt="Sospana Sonke" className="h-10 w-10 rounded-xl object-cover shadow-md" />
            <span className="font-display text-xl font-bold tracking-tight" style={{ color: C.navy }}>
              Sospana&nbsp;<span style={{ color: C.gold }}>Sonke</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/login" className="rounded-xl px-4 py-2 text-sm font-semibold transition hover:bg-black/5" style={{ color: C.navy }}>
              Log in
            </Link>
            <Link
              href="/register"
              className="rounded-xl px-4 py-2 text-sm font-bold text-white shadow-sm transition hover:brightness-110"
              style={{ background: C.navy }}
            >
              Get started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-4 pt-2">
        <div
          className="relative overflow-hidden rounded-t-[2rem] px-6 pb-14 pt-14 text-white shadow-xl sm:px-14 sm:pb-16 sm:pt-20"
          style={{ background: `radial-gradient(120% 120% at 85% 8%, #1a4f7a 0%, ${C.navy} 45%, ${C.ink} 100%)` }}
        >
          <Starfield className="opacity-80" />
          <CursorGlow />
          {/* decorative orbs — a warm sunrise glow behind the continent art */}
          <div
            className="pointer-events-none absolute -right-16 -top-24 h-80 w-80 animate-float-slow rounded-full blur-3xl"
            style={{ background: "radial-gradient(circle at 30% 30%,#ffcf5a,#ff7a1a)", opacity: 0.5 }}
          />
          <div
            className="pointer-events-none absolute -bottom-24 -left-16 h-72 w-72 animate-float rounded-full blur-3xl"
            style={{ background: `radial-gradient(circle at 40% 40%,${C.mint},${C.teal})`, opacity: 0.28 }}
          />
          <div className="pointer-events-none absolute inset-0 bg-noise opacity-[0.05]" />
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.06]"
            style={{ backgroundImage: "radial-gradient(#fff 1px, transparent 1px)", backgroundSize: "22px 22px" }}
          />
          <SavannaSilhouette />

          <div className="relative flex flex-wrap items-center gap-10">
            <div className="min-w-[16rem] flex-1">
              <Reveal>
                <div className="flex items-center gap-3">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src="/logo-mark.png" alt="" className="h-10 w-10 rounded-xl object-cover shadow-md" />
                  <span className="font-display text-2xl font-extrabold tracking-tight">
                    Sospana<span style={{ color: C.gold }}>-Sonke</span>
                  </span>
                </div>
                <p className="mt-1 pl-[3.25rem] text-xs font-medium uppercase tracking-[0.2em] text-blue-200">
                  Together we find opportunities
                </p>
              </Reveal>

              <Reveal delay={80}>
                <span className="mt-6 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-xs font-semibold backdrop-blur-sm">
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75" style={{ background: C.mint }} />
                    <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: C.mint }} />
                  </span>
                  Live across all 54 African nations · The full continent, one platform
                </span>
              </Reveal>

              <Reveal delay={140}>
                <GreetingsMarquee />
              </Reveal>

              <Reveal delay={200}>
                <h1 className="mt-6 font-display text-5xl font-extrabold leading-[1.02] tracking-tight sm:text-7xl">
                  Your Future
                  <br />
                  <span style={{ color: C.gold }}>Is Here</span>
                </h1>
              </Reveal>
              <Reveal delay={260}>
                <p className="mt-6 max-w-xl text-lg leading-relaxed text-blue-100">
                  Sospana Sonke connects job seekers, learners, and communities across{" "}
                  <span className="font-bold" style={{ color: C.gold }}>all 54 African countries</span>{" "}
                  with real opportunities, skills and resources — for a better tomorrow.
                </p>
              </Reveal>

              <Reveal delay={340}>
                <div className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-3">
                  <Link
                    href="/register"
                    className="group relative overflow-hidden rounded-full px-8 py-4 text-base font-extrabold shadow-lg transition hover:brightness-105 hover:-translate-y-0.5"
                    style={{ background: `linear-gradient(120deg,${C.gold},${C.amber})`, color: "#3a2b00" }}
                  >
                    <span className="relative z-10">Get Started →</span>
                    <span className="pointer-events-none absolute inset-0 -translate-x-full skew-x-[-20deg] bg-white/40 opacity-0 transition-all duration-700 group-hover:translate-x-full group-hover:opacity-100" />
                  </Link>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm font-semibold text-blue-200">
                    <Link href="/jobs" className="transition hover:text-white">Find jobs →</Link>
                    <span className="text-white/20">|</span>
                    <Link href="/companies" className="transition hover:text-white">Browse companies</Link>
                    <span className="text-white/20">|</span>
                    <Link href="/jobs?type=SOE&region=South%20Africa" className="transition hover:text-white">🏛️ SOE vacancies (SA)</Link>
                  </div>
                </div>
              </Reveal>

              <Reveal delay={420}>
                <div className="mt-10 grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-4 sm:gap-x-4">
                  {FEATURES.map((f) => (
                    <div key={f.title} className="flex items-start gap-2.5">
                      <FeatureIcon kind={f.kind} />
                      <div>
                        <div className="text-sm font-bold leading-tight text-white">{f.title}</div>
                        <div className="text-xs leading-tight text-blue-200">{f.sub}</div>
                      </div>
                    </div>
                  ))}
                </div>
                <p className="mt-6 text-sm text-blue-200">
                  <b style={{ color: C.gold }}>Free to use</b> · Direct employer links, SOE vacancies &amp; application tracking all included.
                </p>
              </Reveal>
            </div>

            {/* Hero art: the continent, made of its own flags */}
            <Reveal delay={220} className="hidden shrink-0 sm:block">
              <AfricaMosaic />
            </Reveal>
          </div>
        </div>

        <FlagRibbon />
      </section>

      {/* Words to grow by */}
      <section className="mx-auto max-w-4xl px-4 pt-8">
        <Reveal>
          <blockquote className="rounded-2xl border-l-4 bg-white p-6 shadow-sm" style={{ borderColor: C.gold }}>
            <p className="text-base italic leading-relaxed text-gray-700 sm:text-lg">
              &ldquo;Education is the most powerful weapon which you can use to change the world.&rdquo;
            </p>
            <footer className="mt-1.5 text-sm font-semibold" style={{ color: C.navy }}>
              — Nelson Mandela, former President of South Africa
            </footer>
          </blockquote>
        </Reveal>
      </section>

      {/* Trust strip */}
      <section className="mx-auto max-w-6xl px-4">
        <Reveal delay={80}>
          <div className="-mt-6 grid grid-cols-2 gap-3 rounded-2xl bg-white p-4 shadow-lg sm:grid-cols-4">
            {[
              [3439, "+", "Employers tracked", C.red],
              [null, "Direct", "To official careers pages", C.teal],
              [null, "SOE", "Vacancies across South Africa", C.green],
              [null, "Free", "Full access, no charge", C.gold],
            ].map(([n, suffixOrLabel, l, col], i) => (
              <div key={l as string} className="px-3 py-2 text-center">
                <div className="font-display text-2xl font-extrabold" style={{ color: col as string }}>
                  {n === null ? (suffixOrLabel as string) : <CountUp target={n as number} suffix={suffixOrLabel as string} duration={1200 + i * 150} />}
                </div>
                <div className="text-xs font-medium text-gray-500">{l as string}</div>
              </div>
            ))}
          </div>
        </Reveal>
      </section>

      {/* Pillars */}
      <section className="mx-auto grid max-w-6xl gap-5 px-4 py-12 sm:grid-cols-3">
        {[
          ["🎯", "Straight to employers", "Direct links to 3,400+ companies' official careers pages across the region — no middle-man boards, no games.", C.red],
          ["🏛️", "Don't miss the SOEs", "Browse open roles at state-owned enterprises across South Africa and the region — filtered and ready to explore.", C.gold],
          ["📈", "Track & rise", "Every application in one place. Stay organised, stay ready, and keep moving forward.", C.teal],
        ].map(([ic, t, d, col], i) => (
          <Reveal key={t as string} delay={i * 120}>
            <TiltCard>
              <div className="group rounded-2xl bg-white p-7 shadow-sm ring-1 ring-black/5 transition-shadow hover:shadow-xl" style={{ borderTop: `5px solid ${col}` }}>
                <div className="flex h-12 w-12 items-center justify-center rounded-xl text-2xl transition-transform group-hover:scale-110" style={{ background: `${col}1a` }}>
                  {ic}
                </div>
                <h3 className="mt-4 font-display text-lg font-bold" style={{ color: C.navy }}>{t}</h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-600">{d}</p>
              </div>
            </TiltCard>
          </Reveal>
        ))}
      </section>

      {/* Wonders of Africa */}
      <section className="mx-auto max-w-6xl px-4">
        <NdebeleDiamonds id="nd-wonders-top" />
        <div className="relative overflow-hidden px-6 py-12 text-white shadow-xl sm:px-12" style={{ background: `linear-gradient(135deg,${C.ink},#123a2b 60%,#1d5a3a)` }}>
          <div className="pointer-events-none absolute inset-0 bg-noise opacity-[0.05]" />
          <div
            className="pointer-events-none absolute -left-10 -top-10 h-56 w-56 animate-float rounded-full blur-3xl"
            style={{ background: `radial-gradient(circle,${C.sun},transparent 70%)`, opacity: 0.35 }}
          />
          <Reveal className="relative text-center">
            <span className="inline-block rounded-full bg-white/10 px-4 py-1.5 text-xs font-semibold backdrop-blur-sm">✨ Proudly African</span>
            <h2 className="mt-4 font-display text-2xl font-extrabold sm:text-4xl">The wonders of a continent behind you.</h2>
            <p className="mx-auto mt-3 max-w-2xl text-blue-100">
              From the Cape to the Rift Valley, Africa has always built the extraordinary. Your career is the next great thing this continent creates.
            </p>
          </Reveal>
          <div className="relative mt-9 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            {WONDERS.map((w, i) => (
              <Reveal key={w.name} delay={(i % 6) * 70}>
                <TiltCard>
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-center backdrop-blur-sm transition-colors hover:border-white/25 hover:bg-white/10">
                    <svg viewBox="0 0 72 52" className="mx-auto h-14 w-full" aria-hidden="true">{w.art}</svg>
                    <div className="mt-2 text-sm font-bold">{w.name}</div>
                    <div className="text-[11px] text-blue-200">{w.place}</div>
                  </div>
                </TiltCard>
              </Reveal>
            ))}
          </div>
        </div>
        <NdebeleDiamonds id="nd-wonders-bottom" />
      </section>

      {/* SADC region */}
      <section className="mx-auto max-w-6xl px-4 pt-12">
        <div className="relative overflow-hidden rounded-[2rem] px-6 py-12 text-white shadow-xl sm:px-12" style={{ background: `linear-gradient(135deg,${C.ink},${C.navy} 55%,#155e45)` }}>
          <div className="pointer-events-none absolute inset-0 bg-noise opacity-[0.05]" />
          <div
            className="pointer-events-none absolute -right-10 -top-10 h-56 w-56 animate-float-slow rounded-full blur-3xl"
            style={{ background: `radial-gradient(circle,${C.gold},transparent 70%)`, opacity: 0.4 }}
          />
          <div className="relative">
            <Reveal>
              <span className="inline-block rounded-full bg-white/10 px-4 py-1.5 text-xs font-semibold backdrop-blur-sm">🌍 Africa&apos;s Opportunity Map</span>
              <h2 className="mt-4 font-display text-2xl font-extrabold sm:text-4xl">Built for the region. Live across Africa.</h2>
              <p className="mt-3 max-w-3xl text-blue-100">
                We&apos;re live across all 54 African nations — every SADC member state plus every other country across West, Central, East and North Africa. For a few of our newest markets we start with state-owned employers while their stock-exchange listings are added. Wherever you are, your ambition has a home here.
              </p>
            </Reveal>

            {/* Live now */}
            <div className="mt-8">
              <p className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-blue-200">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75" style={{ background: C.mint }} />
                  <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: C.mint }} />
                </span>
                Live now
              </p>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                {LIVE.map((c, i) => (
                  <Reveal key={c.name} delay={(i % 4) * 70}>
                    <div className="flex items-center gap-3 rounded-2xl border border-white/15 bg-white/10 p-4 backdrop-blur-sm transition-colors hover:border-white/30 hover:bg-white/[0.15]">
                      <span className="text-4xl leading-none">{c.flag}</span>
                      <div>
                        <div className="text-sm font-bold leading-tight">{c.name}</div>
                        <div className="mt-0.5 text-xs font-semibold" style={{ color: C.mint }}>
                          <CountUp target={c.count} suffix=" employers" duration={1000} />
                        </div>
                        <span className="mt-1 inline-block rounded-full px-2 py-0.5 text-[10px] font-bold" style={{ background: C.green, color: "#fff" }}>● Live</span>
                        {c.pending && <div className="mt-1 text-[10px] font-medium text-blue-200">Stock exchange listings coming soon</div>}
                      </div>
                    </div>
                  </Reveal>
                ))}
              </div>
            </div>

            <p className="mt-5 text-sm font-semibold text-blue-100">
              🎉 Live across all 54 African nations — the full continent, one platform.
            </p>

            {/* Contribution ranking — which country is powering the most opportunities */}
            <Reveal delay={100}>
              <div className="mt-8 rounded-2xl border border-white/10 bg-black/20 p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-blue-200">Who&apos;s powering Africa&apos;s opportunities</p>
                <p className="mt-1 text-sm text-blue-100">Verified employers on Sospana Sonke by country — a live picture of where the region&apos;s opportunities are opening up.</p>
                <div className="mt-4 space-y-2.5">
                  {LIVE.map((c, i) => {
                    const max = LIVE[0].count || 1;
                    const pct = Math.max(6, Math.round((c.count / max) * 100));
                    const cols = [C.gold, C.mint, C.sky, C.green, C.sun, C.plum, C.red, C.teal, C.amber, C.mint, C.sky, C.green, C.gold, C.sun, C.teal, C.plum];
                    const col = cols[i % cols.length];
                    return (
                      <BarRow key={c.name} name={c.name} flag={c.flag} pct={pct} count={c.count} color={col} delay={i * 60} />
                    );
                  })}
                </div>
                <p className="mt-3 text-[11px] text-blue-200">South Africa leads today; as we verify more employers across each market, this picture will keep shifting.</p>
              </div>
            </Reveal>

            {/* Coming soon */}
            {SOON.length > 0 && (
              <Reveal delay={140}>
                <div className="mt-5">
                  <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-blue-200">Coming soon across Africa</p>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {SOON.map((c) => (
                      <div key={c.name} className="rounded-xl border border-white/10 bg-white/5 p-3 text-center transition hover:bg-white/10">
                        <div className="text-3xl">{c.flag}</div>
                        <div className="mt-1 text-sm font-semibold">{c.name}</div>
                        <div className="mt-1 inline-block rounded-full bg-white/10 px-2 py-0.5 text-[10px] font-semibold text-blue-100">Coming soon</div>
                      </div>
                    ))}
                  </div>
                </div>
              </Reveal>
            )}
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
                  <span key={l} className="rounded-full px-3 py-1 text-xs font-semibold transition hover:-translate-y-0.5" style={{ background: `${col}18`, color: col }}>
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
          <p className="mt-2 text-center text-gray-500">Four simple steps from profile to progress.</p>
        </Reveal>
        <div className="mt-8 grid gap-5 sm:grid-cols-4">
          {[
            ["1", "Create your profile", "Add your details and upload your CV — once.", C.red],
            ["2", "Search jobs", "Find roles by title across every employer we track.", C.sun],
            ["3", "Apply direct", "Apply straight on the employer's official page — no middle-man.", C.green],
            ["4", "Track & win", "Follow every application in one place.", C.sky],
          ].map(([n, t, d, col], i) => (
            <Reveal key={n as string} delay={i * 100}>
              <div className="relative rounded-2xl bg-white p-6 shadow-sm ring-1 ring-black/5 transition hover:-translate-y-1 hover:shadow-md">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl font-display text-lg font-extrabold text-white shadow-md" style={{ background: col as string }}>{n}</div>
                <h4 className="mt-4 font-bold" style={{ color: C.navy }}>{t}</h4>
                <p className="mt-1.5 text-sm leading-relaxed text-gray-600">{d}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section className="mx-auto max-w-6xl px-4 py-12">
        <Reveal>
          <div className="relative overflow-hidden rounded-[2rem] px-6 py-14 text-center shadow-xl" style={{ background: `linear-gradient(120deg,${C.red},${C.sun} 45%,${C.gold})` }}>
            <div className="pointer-events-none absolute inset-0 opacity-10" style={{ backgroundImage: "radial-gradient(#000 1px, transparent 1px)", backgroundSize: "20px 20px" }} />
            <div className="pointer-events-none absolute -inset-1 animate-pulse-glow rounded-[2rem]" style={{ boxShadow: `0 0 90px 10px ${C.gold}66` }} />
            <div className="relative">
              <h2 className="font-display text-3xl font-extrabold sm:text-4xl" style={{ color: "#2a1400" }}>Your ambition deserves a real platform.</h2>
              <p className="mx-auto mt-3 max-w-xl text-lg" style={{ color: "#3a1e00" }}>Build your profile, explore open vacancies, and start applying with confidence today.</p>
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
        </Reveal>
      </section>

      <NdebeleStripe id="nd-bottom" />
      <footer className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-8 text-sm text-gray-500">
        <span>© 2026 Sospana Sonke · Southern Africa</span>
        <div className="flex items-center gap-4">
          <Link href="/donate" className="hover:text-gray-800">Donate</Link>
          <a href="/privacy.html" className="hover:text-gray-800">Privacy Policy</a>
        </div>
      </footer>
    </div>
  );
}

/* Animated ranking bar — fills to its percentage only once it scrolls into view. */
function BarRow({ name, flag, pct, count, color, delay }: { name: string; flag: string; pct: number; count: number; color: string; delay: number }) {
  const { ref, visible } = useReveal<HTMLDivElement>(0.4);
  return (
    <div ref={ref} className="flex items-center gap-3">
      <div className="flex w-28 shrink-0 items-center gap-1.5 text-sm font-semibold sm:w-36">
        <span>{flag}</span><span className="truncate">{name}</span>
      </div>
      <div className="relative h-6 flex-1 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full transition-[width] duration-1000 ease-out"
          style={{ width: visible ? `${pct}%` : "0%", background: color, transitionDelay: `${delay}ms` }}
        />
      </div>
      <div className="w-8 shrink-0 text-right text-sm font-bold tabular-nums">{count}</div>
    </div>
  );
}
