"use client";

import { useEffect, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

const C = {
  navy: "#0b1f3a", ink: "#071528", gold: "#f5b301", amber: "#ff9e2c",
  teal: "#0f9d8f", mint: "#5fe0d0", red: "#e4322b", green: "#1a9e5f",
  sky: "#2f9bf6", plum: "#7c3aed", sun: "#ff7a1a", cream: "#faf6ee",
};

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
  { name: "South Africa", flag: "🇿🇦", count: 368, pending: false },
  { name: "Zimbabwe", flag: "🇿🇼", count: 67, pending: false },
  { name: "Namibia", flag: "🇳🇦", count: 46, pending: false },
  { name: "Botswana", flag: "🇧🇼", count: 42, pending: false },
  { name: "Mozambique", flag: "🇲🇿", count: 33, pending: false },
  { name: "Eswatini", flag: "🇸🇿", count: 30, pending: false },
  { name: "Malawi", flag: "🇲🇼", count: 25, pending: true },
  { name: "Mauritius", flag: "🇲🇺", count: 24, pending: true },
  { name: "Zambia", flag: "🇿🇲", count: 22, pending: true },
  { name: "Lesotho", flag: "🇱🇸", count: 17, pending: false },
  { name: "Tanzania", flag: "🇹🇿", count: 16, pending: true },
  { name: "Angola", flag: "🇦🇴", count: 11, pending: true },
];
const SOON = [
  { name: "Madagascar", flag: "🇲🇬" },
  { name: "DR Congo", flag: "🇨🇩" },
  { name: "Seychelles", flag: "🇸🇨" },
  { name: "Comoros", flag: "🇰🇲" },
];

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

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!loading && user) router.replace("/companies");
  }, [loading, user, router]);

  return (
    <div className="landing -mx-4 -my-6" style={{ background: C.cream }}>
      <NdebeleStripe id="nd-top" />

      {/* Header */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl font-extrabold text-white shadow-md"
            style={{ background: "conic-gradient(from 210deg,#ff6b5b,#f5b301,#1a9e5f,#2f9bf6,#7c3aed,#ff6b5b)" }}>SS</span>
          <span className="text-xl font-bold tracking-tight" style={{ color: C.navy }}>Sospana&nbsp;<span style={{ color: C.gold }}>Sonke</span></span>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/login" className="rounded-xl px-4 py-2 text-sm font-semibold transition hover:bg-black/5" style={{ color: C.navy }}>Log in</Link>
          <Link href="/register" className="rounded-xl px-4 py-2 text-sm font-bold text-white shadow-sm transition hover:brightness-110" style={{ background: C.navy }}>Get started</Link>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-4">
        <div className="relative overflow-hidden rounded-[2rem] px-6 py-14 text-white shadow-xl sm:px-14 sm:py-20"
          style={{ background: `radial-gradient(120% 120% at 85% 8%, #1a4f7a 0%, ${C.navy} 45%, ${C.ink} 100%)` }}>
          {/* decorative orbs */}
          <div className="pointer-events-none absolute -right-16 -top-24 h-80 w-80 rounded-full blur-3xl" style={{ background: "radial-gradient(circle at 30% 30%,#ffcf5a,#ff7a1a)", opacity: 0.55 }} />
          <div className="pointer-events-none absolute -bottom-24 -left-16 h-72 w-72 rounded-full blur-3xl" style={{ background: `radial-gradient(circle at 40% 40%,${C.mint},${C.teal})`, opacity: 0.3 }} />
          <div className="pointer-events-none absolute inset-0 opacity-[0.06]"
            style={{ backgroundImage: "radial-gradient(#fff 1px, transparent 1px)", backgroundSize: "22px 22px" }} />
          <SavannaSilhouette />

          <div className="relative flex flex-wrap items-center gap-10">
            <div className="min-w-[16rem] flex-1">
              <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-xs font-semibold backdrop-blur-sm">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75" style={{ background: C.mint }} />
                  <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: C.mint }} />
                </span>
                Live across 12 African markets · Growing across the continent
              </span>

              <div className="mb-5 mt-6 flex flex-wrap gap-2">
                {GREETINGS.map(([word, bg]) => (
                  <span key={word} className="rounded-full px-3 py-1 text-xs font-bold" style={{ background: bg, color: bg === C.gold ? "#4a3600" : "#fff" }}>{word}</span>
                ))}
              </div>

              <h1 className="text-4xl font-extrabold leading-[1.05] tracking-tight sm:text-6xl">
                Where talent meets<br />
                <span style={{ color: C.gold }}>opportunity.</span>
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-relaxed text-blue-100">
                A professional job-search platform that connects ambitious young people directly to real employers — tailoring your CV truthfully to each role and tracking every application in one place.
              </p>

              {/* Words to grow by */}
              <blockquote className="mt-7 max-w-xl rounded-r-xl border-l-4 pl-4" style={{ borderColor: C.gold }}>
                <p className="text-base italic leading-relaxed text-white sm:text-lg">
                  &ldquo;Education is the most powerful weapon which you can use to change the world.&rdquo;
                </p>
                <footer className="mt-1.5 text-sm font-semibold" style={{ color: C.gold }}>
                  — Nelson Mandela, former President of South Africa
                </footer>
              </blockquote>

              <div className="mt-8 flex flex-wrap gap-3">
                <Link href="/register" className="rounded-xl px-6 py-3.5 font-extrabold shadow-lg transition hover:brightness-105" style={{ background: `linear-gradient(120deg,${C.gold},${C.amber})`, color: "#3a2b00" }}>Create your free account →</Link>
                <Link href="/jobs" className="rounded-xl px-6 py-3.5 font-bold text-white shadow-lg transition hover:brightness-110" style={{ background: C.teal }}>Find jobs →</Link>
                <Link href="/companies" className="rounded-xl border border-white/40 bg-white/5 px-6 py-3.5 font-semibold text-white backdrop-blur-sm transition hover:bg-white/10">Browse companies</Link>
              </div>
              <p className="mt-6 text-sm text-blue-200"><b style={{ color: C.gold }}>Free to use</b> · CV tailoring, cover letters &amp; application tracking all included.</p>
            </div>

            {/* Hero art: sunrise over township skyline */}
            <div className="hidden shrink-0 sm:block">
              <svg viewBox="0 0 320 320" width="300" height="300" aria-hidden="true">
                <circle cx="160" cy="175" r="132" fill="rgba(255,255,255,.05)" />
                <circle cx="160" cy="175" r="96" fill="rgba(255,255,255,.04)" />
                <path d="M160 175 L160 44 L194 66 Z" fill={C.gold} />
                <path d="M160 175 L226 74 L250 110 Z" fill={C.sun} />
                <path d="M160 175 L262 138 L268 178 Z" fill={C.red} />
                <path d="M160 175 L160 44 L126 66 Z" fill={C.green} />
                <path d="M160 175 L94 74 L70 110 Z" fill={C.sky} />
                <path d="M160 175 L58 138 L52 178 Z" fill={C.plum} />
                <circle cx="160" cy="175" r="38" fill={C.gold} stroke="#0b0b0b" strokeWidth="3" />
                <g fill="#071528">
                  <rect x="44" y="220" width="36" height="60" /><rect x="86" y="202" width="44" height="78" />
                  <rect x="136" y="228" width="32" height="52" /><rect x="174" y="196" width="48" height="84" />
                  <rect x="228" y="220" width="36" height="60" />
                </g>
                <g fill={C.gold}><rect x="98" y="218" width="8" height="9" /><rect x="114" y="218" width="8" height="9" /><rect x="186" y="212" width="8" height="9" /><rect x="202" y="212" width="8" height="9" /></g>
                <rect x="22" y="278" width="276" height="6" fill="#0b0b0b" />
              </svg>
            </div>
          </div>
        </div>
      </section>

      {/* Trust strip */}
      <section className="mx-auto max-w-6xl px-4">
        <div className="-mt-6 grid grid-cols-2 gap-3 rounded-2xl bg-white p-4 shadow-lg sm:grid-cols-4">
          {[
            ["700+", "Employers tracked", C.red],
            ["Direct", "To official careers pages", C.teal],
            ["100%", "Truthful CV tailoring", C.green],
            ["Free", "Full access, no charge", C.gold],
          ].map(([n, l, col]) => (
            <div key={l as string} className="px-3 py-2 text-center">
              <div className="text-2xl font-extrabold" style={{ color: col as string }}>{n}</div>
              <div className="text-xs font-medium text-gray-500">{l}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Pillars */}
      <section className="mx-auto grid max-w-6xl gap-5 px-4 py-12 sm:grid-cols-3">
        {[
          ["🎯", "Straight to employers", "Direct links to 700+ companies' official careers pages across the region — no middle-man boards, no games.", C.red],
          ["✍️", "Apply smarter", "We tailor your CV and cover letter to each role — truthfully, from your real story. Never invented.", C.gold],
          ["📈", "Track & rise", "Every application in one place. Stay organised, stay ready, and keep moving forward.", C.teal],
        ].map(([ic, t, d, col]) => (
          <div key={t as string} className="group rounded-2xl bg-white p-7 shadow-sm ring-1 ring-black/5 transition hover:-translate-y-1 hover:shadow-lg" style={{ borderTop: `5px solid ${col}` }}>
            <div className="flex h-12 w-12 items-center justify-center rounded-xl text-2xl" style={{ background: `${col}1a` }}>{ic}</div>
            <h3 className="mt-4 text-lg font-bold" style={{ color: C.navy }}>{t}</h3>
            <p className="mt-2 text-sm leading-relaxed text-gray-600">{d}</p>
          </div>
        ))}
      </section>

      {/* Wonders of Africa */}
      <section className="mx-auto max-w-6xl px-4">
        <NdebeleDiamonds id="nd-wonders-top" />
        <div className="relative overflow-hidden px-6 py-12 text-white shadow-xl sm:px-12" style={{ background: `linear-gradient(135deg,${C.ink},#123a2b 60%,#1d5a3a)` }}>
          <div className="pointer-events-none absolute -left-10 -top-10 h-56 w-56 rounded-full blur-3xl" style={{ background: `radial-gradient(circle,${C.sun},transparent 70%)`, opacity: 0.35 }} />
          <div className="relative text-center">
            <span className="inline-block rounded-full bg-white/10 px-4 py-1.5 text-xs font-semibold backdrop-blur-sm">✨ Proudly African</span>
            <h2 className="mt-4 text-2xl font-extrabold sm:text-4xl">The wonders of a continent behind you.</h2>
            <p className="mx-auto mt-3 max-w-2xl text-blue-100">
              From the Cape to the Rift Valley, Africa has always built the extraordinary. Your career is the next great thing this continent creates.
            </p>
          </div>
          <div className="relative mt-9 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            {WONDERS.map((w) => (
              <div key={w.name} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-center backdrop-blur-sm transition hover:-translate-y-1 hover:bg-white/10">
                <svg viewBox="0 0 72 52" className="mx-auto h-14 w-full" aria-hidden="true">{w.art}</svg>
                <div className="mt-2 text-sm font-bold">{w.name}</div>
                <div className="text-[11px] text-blue-200">{w.place}</div>
              </div>
            ))}
          </div>
        </div>
        <NdebeleDiamonds id="nd-wonders-bottom" />
      </section>

      {/* SADC region */}
      <section className="mx-auto max-w-6xl px-4 pt-12">
        <div className="relative overflow-hidden rounded-[2rem] px-6 py-12 text-white shadow-xl sm:px-12" style={{ background: `linear-gradient(135deg,${C.ink},${C.navy} 55%,#155e45)` }}>
          <div className="pointer-events-none absolute -right-10 -top-10 h-56 w-56 rounded-full blur-3xl" style={{ background: `radial-gradient(circle,${C.gold},transparent 70%)`, opacity: 0.4 }} />
          <div className="relative">
            <span className="inline-block rounded-full bg-white/10 px-4 py-1.5 text-xs font-semibold backdrop-blur-sm">🌍 Africa&apos;s Opportunity Map</span>
            <h2 className="mt-4 text-2xl font-extrabold sm:text-4xl">Built for the region. Live across Africa.</h2>
            <p className="mt-3 max-w-3xl text-blue-100">
              We&apos;re live in twelve African markets — from South Africa across the SADC region to Tanzania. For our newest markets we start with state-owned employers while their stock-exchange listings are added. Wherever you are, your ambition has a home here.
            </p>

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
                {LIVE.map((c) => (
                  <div key={c.name} className="flex items-center gap-3 rounded-2xl border border-white/15 bg-white/10 p-4 backdrop-blur-sm">
                    <span className="text-4xl leading-none">{c.flag}</span>
                    <div>
                      <div className="text-sm font-bold leading-tight">{c.name}</div>
                      <div className="mt-0.5 text-xs font-semibold" style={{ color: C.mint }}>{c.count} employers</div>
                      <span className="mt-1 inline-block rounded-full px-2 py-0.5 text-[10px] font-bold" style={{ background: C.green, color: "#fff" }}>● Live</span>
                      {c.pending && <div className="mt-1 text-[10px] font-medium text-blue-200">Stock exchange listings coming soon</div>}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <p className="mt-5 text-sm font-semibold text-blue-100">
              🎉 Live across twelve African markets — with more of the continent to follow.
            </p>

            {/* Contribution ranking — which country is powering the most opportunities */}
            <div className="mt-8 rounded-2xl border border-white/10 bg-black/20 p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-blue-200">Who&apos;s powering Africa&apos;s opportunities</p>
              <p className="mt-1 text-sm text-blue-100">Verified employers on Sospana Sonke by country — a live picture of where the region&apos;s opportunities are opening up.</p>
              <div className="mt-4 space-y-2.5">
                {LIVE.map((c, i) => {
                  const max = LIVE[0].count || 1;
                  const pct = Math.max(6, Math.round((c.count / max) * 100));
                  const cols = [C.gold, C.mint, C.sky, C.green, C.sun, C.plum, C.red, C.teal, C.amber, C.mint, C.sky, C.green];
                  const col = cols[i % cols.length];
                  return (
                    <div key={c.name} className="flex items-center gap-3">
                      <div className="flex w-28 shrink-0 items-center gap-1.5 text-sm font-semibold sm:w-36">
                        <span>{c.flag}</span><span className="truncate">{c.name}</span>
                      </div>
                      <div className="relative h-6 flex-1 overflow-hidden rounded-full bg-white/10">
                        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: col }} />
                      </div>
                      <div className="w-8 shrink-0 text-right text-sm font-bold tabular-nums">{c.count}</div>
                    </div>
                  );
                })}
              </div>
              <p className="mt-3 text-[11px] text-blue-200">South Africa leads today; as we verify more employers across each market, this picture will keep shifting.</p>
            </div>

            {/* Coming soon */}
            {SOON.length > 0 && (
              <div className="mt-5">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-blue-200">Coming soon across SADC</p>
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
            )}
          </div>
        </div>
      </section>

      {/* Proud band */}
      <section className="mx-auto max-w-6xl px-4 py-12">
        <div className="rounded-3xl bg-white px-6 py-9 shadow-sm ring-1 ring-black/5 sm:px-10">
          <h2 className="text-2xl font-extrabold sm:text-3xl" style={{ color: C.navy }}>Built for every young African. 🌍</h2>
          <p className="mt-3 max-w-3xl text-gray-600">
            Wherever you come from and whatever you dream in, your ambition speaks a language every employer
            understands: skill, effort, and the will to rise. One continent, one generation ready to work —
            and one platform standing behind you every step of the way.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            {VALUES.map((l, i) => {
              const cols = [C.red, C.sun, C.gold, C.green, C.teal, C.sky, C.plum];
              const col = cols[i % cols.length];
              return <span key={l} className="rounded-full px-3 py-1 text-xs font-semibold" style={{ background: `${col}18`, color: col }}>{l}</span>;
            })}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-6xl px-4 pb-4">
        <h2 className="text-center text-2xl font-extrabold sm:text-3xl" style={{ color: C.navy }}>How it works</h2>
        <p className="mt-2 text-center text-gray-500">Four simple steps from profile to progress.</p>
        <div className="mt-8 grid gap-5 sm:grid-cols-4">
          {[
            ["1", "Create your profile", "Add your details and upload your CV — once.", C.red],
            ["2", "Search jobs", "Find roles by title across every employer we track.", C.sun],
            ["3", "Tailor & apply", "Get a CV built for the role, then apply direct.", C.green],
            ["4", "Track & win", "Follow every application in one place.", C.sky],
          ].map(([n, t, d, col]) => (
            <div key={n as string} className="relative rounded-2xl bg-white p-6 shadow-sm ring-1 ring-black/5">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl text-lg font-extrabold text-white shadow-md" style={{ background: col as string }}>{n}</div>
              <h4 className="mt-4 font-bold" style={{ color: C.navy }}>{t}</h4>
              <p className="mt-1.5 text-sm leading-relaxed text-gray-600">{d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section className="mx-auto max-w-6xl px-4 py-12">
        <div className="relative overflow-hidden rounded-[2rem] px-6 py-14 text-center shadow-xl" style={{ background: `linear-gradient(120deg,${C.red},${C.sun} 45%,${C.gold})` }}>
          <div className="pointer-events-none absolute inset-0 opacity-10" style={{ backgroundImage: "radial-gradient(#000 1px, transparent 1px)", backgroundSize: "20px 20px" }} />
          <div className="relative">
            <h2 className="text-3xl font-extrabold sm:text-4xl" style={{ color: "#2a1400" }}>Your ambition deserves a real platform.</h2>
            <p className="mx-auto mt-3 max-w-xl text-lg" style={{ color: "#3a1e00" }}>Build your profile, tailor your CV, and start applying with confidence today.</p>
            <Link href="/register" className="mt-7 inline-block rounded-xl px-8 py-4 text-lg font-extrabold text-white shadow-lg transition hover:brightness-110" style={{ background: C.navy }}>Get started today →</Link>
          </div>
        </div>
      </section>

      <NdebeleStripe id="nd-bottom" />
      <footer className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-8 text-sm text-gray-500">
        <span>© 2026 Sospana Sonke · Southern Africa</span>
        <a href="/privacy.html" className="hover:text-gray-800">Privacy Policy</a>
      </footer>
    </div>
  );
}
