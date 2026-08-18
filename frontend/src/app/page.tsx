"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

const C = {
  navy: "#0b2447", gold: "#f5b301", teal: "#0f9d8f", red: "#e4322b",
  green: "#1a9e5f", sky: "#2f9bf6", plum: "#7c3aed", sun: "#ff7a1a", cream: "#fbf7ee",
};

function NdebeleStripe({ id }: { id: string }) {
  return (
    <svg className="block w-full" height={20} preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <pattern id={id} width="88" height="20" patternUnits="userSpaceOnUse">
          <rect width="88" height="20" fill="#0b0b0b" />
          <rect x="1" y="1" width="20" height="18" fill={C.red} />
          <rect x="23" y="1" width="20" height="18" fill={C.gold} />
          <rect x="45" y="1" width="20" height="18" fill={C.green} />
          <rect x="67" y="1" width="20" height="18" fill={C.sky} />
          <path d="M1 1 L11 10 L21 1 Z" fill="#0b0b0b" />
          <path d="M45 19 L55 10 L65 19 Z" fill="#0b0b0b" />
          <path d="M23 19 L33 10 L43 19 Z" fill="#fff" opacity="0.85" />
          <path d="M67 1 L77 10 L87 1 Z" fill="#fff" opacity="0.85" />
        </pattern>
      </defs>
      <rect width="100%" height="20" fill={`url(#${id})`} />
    </svg>
  );
}

const GREETINGS = [
  ["Sawubona", C.red], ["Molo", C.sky], ["Dumela", C.green],
  ["Lotjhani", C.gold], ["Avuxeni", C.plum], ["Ndaa", C.sun],
] as const;

const LANGS = ["isiZulu", "isiXhosa", "Sesotho", "isiNdebele", "Setswana", "Xitsonga", "Tshivenda", "siSwati", "Sepedi", "Afrikaans", "English"];

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
          <span className="flex h-10 w-10 items-center justify-center rounded-xl font-extrabold text-white"
            style={{ background: "conic-gradient(from 210deg,#ff6b5b,#f5b301,#1a9e5f,#2f9bf6,#7c3aed,#ff6b5b)" }}>SS</span>
          <span className="text-xl font-bold" style={{ color: C.navy }}>Sospana&nbsp;<span style={{ color: C.gold }}>Sonke</span></span>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/login" className="rounded-xl px-4 py-2 text-sm font-semibold" style={{ color: C.navy }}>Log in</Link>
          <Link href="/register" className="rounded-xl px-4 py-2 text-sm font-bold text-white" style={{ background: C.navy }}>Get started</Link>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-4">
        <div className="relative overflow-hidden rounded-3xl px-6 py-12 text-white sm:px-12 sm:py-14"
          style={{ background: `linear-gradient(135deg,${C.navy} 0%,#123a6b 42%,#0f766e 78%,#155e45 100%)` }}>
          <div className="pointer-events-none absolute -right-10 -top-16 h-64 w-64 rounded-full blur-2xl" style={{ background: "radial-gradient(circle at 30% 30%,#ffcf5a,#ff7a1a)", opacity: 0.5 }} />
          <div className="relative flex flex-wrap items-center gap-8">
            <div className="min-w-[16rem] flex-1">
              <div className="mb-4 flex flex-wrap gap-2">
                {GREETINGS.map(([word, bg]) => (
                  <span key={word} className="rounded-full px-3 py-1 text-xs font-bold text-white" style={{ background: bg, color: bg === C.gold ? "#4a3600" : "#fff" }}>{word}</span>
                ))}
              </div>
              <h1 className="text-4xl font-extrabold leading-none sm:text-6xl">
                Kasi to <span style={{ color: C.gold }}>career.</span><br />
                Your future, <span style={{ color: "#5fe0d0" }}>your move.</span>
              </h1>
              <p className="mt-5 max-w-xl text-lg text-blue-100">
                From every street, every township, every village — young South Africans are ready. We connect you straight to real employers, and help you apply smarter.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Link href="/register" className="rounded-xl px-6 py-3 font-extrabold shadow-lg" style={{ background: C.gold, color: "#3a2b00" }}>Get started free →</Link>
                <Link href="/login" className="rounded-xl border-2 px-6 py-3 font-semibold text-white" style={{ borderColor: "rgba(255,255,255,.5)" }}>Browse companies</Link>
              </div>
              <p className="mt-5 text-sm text-blue-200">One subscription · <b style={{ color: C.gold }}>R100/month</b> · CV tailoring, cover letters &amp; tracking included.</p>
            </div>
            <div className="hidden shrink-0 sm:block">
              <svg viewBox="0 0 300 300" width="280" height="280" aria-hidden="true">
                <circle cx="150" cy="165" r="120" fill="rgba(255,255,255,.05)" />
                <path d="M150 165 L150 40 L182 60 Z" fill={C.gold} />
                <path d="M150 165 L210 70 L232 104 Z" fill={C.sun} />
                <path d="M150 165 L245 130 L250 168 Z" fill={C.red} />
                <path d="M150 165 L150 40 L118 60 Z" fill={C.green} />
                <path d="M150 165 L90 70 L68 104 Z" fill={C.sky} />
                <path d="M150 165 L55 130 L50 168 Z" fill={C.plum} />
                <circle cx="150" cy="165" r="34" fill={C.gold} stroke="#0b0b0b" strokeWidth="3" />
                <g fill="#0b1f2a">
                  <rect x="40" y="205" width="34" height="55" /><rect x="80" y="190" width="40" height="70" />
                  <rect x="126" y="212" width="30" height="48" /><rect x="162" y="185" width="44" height="75" />
                  <rect x="212" y="205" width="34" height="55" />
                </g>
                <g fill={C.gold}><rect x="90" y="205" width="8" height="8" /><rect x="104" y="205" width="8" height="8" /><rect x="172" y="200" width="8" height="8" /><rect x="186" y="200" width="8" height="8" /></g>
                <rect x="20" y="258" width="260" height="6" fill="#0b0b0b" />
              </svg>
            </div>
          </div>
        </div>
      </section>

      {/* Pillars */}
      <section className="mx-auto grid max-w-6xl gap-4 px-4 py-10 sm:grid-cols-3">
        {[
          ["🎯", "Straight to employers", "Direct links to 367+ companies' official careers pages — no middle-man boards, no games.", C.red],
          ["✍️", "Apply smarter", "We tailor your CV and cover letter to each role — truthfully, from your real story. Never invented.", C.gold],
          ["📈", "Track & rise", "Every application in one place. Stay organised, stay ready, keep moving forward.", C.teal],
        ].map(([ic, t, d, col]) => (
          <div key={t as string} className="rounded-2xl bg-white p-6 shadow-sm" style={{ borderTop: `6px solid ${col}` }}>
            <div className="text-3xl">{ic}</div>
            <h3 className="mt-2 text-lg font-bold" style={{ color: C.navy }}>{t}</h3>
            <p className="mt-1 text-sm text-gray-600">{d}</p>
          </div>
        ))}
      </section>

      {/* Proud band */}
      <section className="mx-auto max-w-6xl px-4">
        <div className="rounded-3xl px-6 py-8 text-white sm:px-10" style={{ background: C.navy }}>
          <h2 className="text-2xl font-extrabold sm:text-3xl">Built for every young South African. 🇿🇦</h2>
          <p className="mt-3 max-w-3xl text-blue-100">
            Ndebele, Zulu, Sotho, Xhosa, Tswana, Tsonga, Venda, Swati, Pedi and all who call this country home. Your language, your roots, your ambition — one platform behind you.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {LANGS.map((l) => (
              <span key={l} className="rounded-full px-3 py-1 text-xs font-semibold" style={{ background: "rgba(255,255,255,.1)" }}>{l}</span>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-6xl px-4 py-10">
        <h2 className="text-center text-2xl font-extrabold sm:text-3xl" style={{ color: C.navy }}>How it works</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-4">
          {[
            ["1", "Create your profile", "Add your details and upload your CV — once.", C.red],
            ["2", "Search jobs", "Find roles by title across every employer we track.", C.sun],
            ["3", "Tailor & apply", "Get a CV built for the role, then apply direct.", C.green],
            ["4", "Track & win", "Follow every application in one place.", C.sky],
          ].map(([n, t, d, col]) => (
            <div key={n as string} className="rounded-2xl bg-white p-5 shadow-sm">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl text-lg font-extrabold text-white" style={{ background: col }}>{n}</div>
              <h4 className="mt-3 font-semibold" style={{ color: C.navy }}>{t}</h4>
              <p className="mt-1 text-sm text-gray-600">{d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section className="mx-auto max-w-6xl px-4 pb-10">
        <div className="rounded-3xl px-6 py-12 text-center" style={{ background: `linear-gradient(120deg,${C.red},${C.sun} 45%,${C.gold})` }}>
          <h2 className="text-3xl font-extrabold sm:text-4xl" style={{ color: "#2a1400" }}>Your hustle deserves a real shot.</h2>
          <p className="mx-auto mt-3 max-w-xl text-lg" style={{ color: "#3a1e00" }}>Sit down, tighten your CV, and go get it. We&apos;ve got your back.</p>
          <Link href="/register" className="mt-6 inline-block rounded-xl px-8 py-4 text-lg font-extrabold text-white" style={{ background: C.navy }}>Get started today →</Link>
        </div>
      </section>

      <NdebeleStripe id="nd-bottom" />
      <footer className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-8 text-sm text-gray-500">
        <span>© 2026 Sospana Sonke</span>
        <a href="/privacy.html" className="hover:text-gray-800">Privacy Policy</a>
      </footer>
    </div>
  );
}
