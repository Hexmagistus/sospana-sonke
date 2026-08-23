"use client";

import { useEffect } from "react";
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

const GREETINGS = [
  ["Sawubona", C.red], ["Molo", C.sky], ["Dumela", C.green],
  ["Lotjhani", C.gold], ["Avuxeni", C.plum], ["Ndaa", C.sun], ["Hello", C.teal],
] as const;

const LANGS = ["isiZulu", "isiXhosa", "Sesotho", "isiNdebele", "Setswana", "Xitsonga", "Tshivenda", "siSwati", "Sepedi", "Afrikaans", "English"];

const LIVE = { name: "South Africa", flag: "🇿🇦" };
const SOON = [
  { name: "Botswana", flag: "🇧🇼" },
  { name: "Lesotho", flag: "🇱🇸" },
  { name: "Eswatini", flag: "🇸🇿" },
  { name: "Namibia", flag: "🇳🇦" },
  { name: "Zimbabwe", flag: "🇿🇼" },
  { name: "Mozambique", flag: "🇲🇿" },
];

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!loading && user) router.replace("/jobs");
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
          style={{ background: `radial-gradient(120% 120% at 85% 10%, #16406e 0%, ${C.navy} 45%, ${C.ink} 100%)` }}>
          {/* decorative orbs */}
          <div className="pointer-events-none absolute -right-16 -top-24 h-80 w-80 rounded-full blur-3xl" style={{ background: "radial-gradient(circle at 30% 30%,#ffcf5a,#ff7a1a)", opacity: 0.55 }} />
          <div className="pointer-events-none absolute -bottom-24 -left-16 h-72 w-72 rounded-full blur-3xl" style={{ background: `radial-gradient(circle at 40% 40%,${C.mint},${C.teal})`, opacity: 0.35 }} />
          <div className="pointer-events-none absolute inset-0 opacity-[0.06]"
            style={{ backgroundImage: "radial-gradient(#fff 1px, transparent 1px)", backgroundSize: "22px 22px" }} />

          <div className="relative flex flex-wrap items-center gap-10">
            <div className="min-w-[16rem] flex-1">
              <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-xs font-semibold backdrop-blur-sm">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75" style={{ background: C.mint }} />
                  <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: C.mint }} />
                </span>
                Now live in South Africa · Expanding across SADC
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
              <div className="mt-8 flex flex-wrap gap-3">
                <Link href="/register" className="rounded-xl px-6 py-3.5 font-extrabold shadow-lg transition hover:brightness-105" style={{ background: `linear-gradient(120deg,${C.gold},${C.amber})`, color: "#3a2b00" }}>Create your free account →</Link>
                <Link href="/login" className="rounded-xl border border-white/40 bg-white/5 px-6 py-3.5 font-semibold text-white backdrop-blur-sm transition hover:bg-white/10">Browse companies</Link>
              </div>
              <p className="mt-6 text-sm text-blue-200">One subscription · <b style={{ color: C.gold }}>R100/month</b> · CV tailoring, cover letters &amp; application tracking included.</p>
            </div>

            {/* Hero art: sunrise over skyline */}
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
            ["367+", "Employers tracked", C.red],
            ["Direct", "To official careers pages", C.teal],
            ["100%", "Truthful CV tailoring", C.green],
            ["R100", "Per month, all included", C.gold],
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
          ["🎯", "Straight to employers", "Direct links to 367+ companies' official careers pages — no middle-man boards, no games.", C.red],
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

      {/* SADC region */}
      <section className="mx-auto max-w-6xl px-4">
        <div className="relative overflow-hidden rounded-[2rem] px-6 py-12 text-white shadow-xl sm:px-12" style={{ background: `linear-gradient(135deg,${C.ink},${C.navy} 55%,#155e45)` }}>
          <div className="pointer-events-none absolute -right-10 -top-10 h-56 w-56 rounded-full blur-3xl" style={{ background: `radial-gradient(circle,${C.gold},transparent 70%)`, opacity: 0.4 }} />
          <div className="relative">
            <span className="inline-block rounded-full bg-white/10 px-4 py-1.5 text-xs font-semibold backdrop-blur-sm">🌍 One platform for Southern Africa</span>
            <h2 className="mt-4 text-2xl font-extrabold sm:text-4xl">Built for the region. Expanding across SADC.</h2>
            <p className="mt-3 max-w-3xl text-blue-100">
              We&apos;re live in South Africa today, and rolling out to neighbouring SADC countries next. Wherever you are in the region, your ambition will have a home here.
            </p>

            {/* Live now */}
            <div className="mt-8 flex flex-wrap items-center gap-4 rounded-2xl border border-white/15 bg-white/10 p-5 backdrop-blur-sm">
              <span className="text-5xl leading-none">{LIVE.flag}</span>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-lg font-bold">{LIVE.name}</span>
                  <span className="rounded-full px-2.5 py-0.5 text-xs font-bold" style={{ background: C.green, color: "#fff" }}>● Live now</span>
                </div>
                <p className="text-sm text-blue-100">Full platform available — search jobs, tailor your CV, and apply today.</p>
              </div>
            </div>

            {/* Coming soon */}
            <div className="mt-5">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-blue-200">Coming soon</p>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                {SOON.map((c) => (
                  <div key={c.name} className="rounded-xl border border-white/10 bg-white/5 p-3 text-center transition hover:bg-white/10">
                    <div className="text-3xl">{c.flag}</div>
                    <div className="mt-1 text-sm font-semibold">{c.name}</div>
                    <div className="mt-1 inline-block rounded-full bg-white/10 px-2 py-0.5 text-[10px] font-semibold text-blue-100">Coming soon</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Proud band */}
      <section className="mx-auto max-w-6xl px-4 py-12">
        <div className="rounded-3xl bg-white px-6 py-9 shadow-sm ring-1 ring-black/5 sm:px-10">
          <h2 className="text-2xl font-extrabold sm:text-3xl" style={{ color: C.navy }}>Built for every young African. 🌍</h2>
          <p className="mt-3 max-w-3xl text-gray-600">
            Zulu, Xhosa, Sotho, Tswana, Ndebele, Tsonga, Venda, Swati, Pedi, Afrikaans, English — and every language of the region to come. Your roots, your language, your ambition — one platform behind you.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            {LANGS.map((l, i) => {
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
