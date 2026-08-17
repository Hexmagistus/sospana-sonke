"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

const NAVY = "#0b1f3a";
const GOLD = "#f5b301";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [loading, user, router]);

  return (
    <div className="-mx-4 -my-6">
      {/* Header */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <div className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand font-extrabold text-white">SS</span>
          <span className="text-lg font-bold" style={{ color: NAVY }}>Sospana&nbsp;Sonke</span>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/login" className="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100">Log in</Link>
          <Link href="/register" className="rounded-lg px-4 py-2 text-sm font-semibold text-white" style={{ background: NAVY }}>Get started</Link>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-4">
        <div className="overflow-hidden rounded-3xl px-6 py-16 text-white sm:px-14" style={{ background: `linear-gradient(135deg, ${NAVY} 0%, #12305c 60%, #0f766e 100%)` }}>
          <p className="mb-3 text-sm font-semibold tracking-widest" style={{ color: GOLD }}>JOB SEARCH · SMARTER · DIRECT</p>
          <h1 className="max-w-3xl text-4xl font-extrabold leading-tight sm:text-6xl">
            Your next <span style={{ color: GOLD }}>opportunity</span> starts here.
          </h1>
          <p className="mt-5 max-w-2xl text-lg text-blue-100">
            We surface real vacancies across <strong>367+ JSE-listed companies and State-Owned Entities</strong> — with direct links to their official careers pages. You apply smarter.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/register" className="rounded-xl px-6 py-3 font-semibold text-black shadow-lg" style={{ background: GOLD }}>Get started free</Link>
            <Link href="/login" className="rounded-xl border border-white/40 px-6 py-3 font-semibold text-white hover:bg-white/10">Browse companies</Link>
          </div>
          <p className="mt-6 text-sm text-blue-200">One subscription · <strong>R100/month</strong> · CV tailoring, cover letters &amp; tracking included — no extra fees.</p>
        </div>
      </section>

      {/* Pillars */}
      <section className="mx-auto grid max-w-6xl gap-4 px-4 py-12 sm:grid-cols-3">
        {[
          ["Direct access", "Straight to employers' official careers pages — no middle-man job boards."],
          ["Apply with confidence", "AI tailors your CV and cover letter truthfully — never inventing facts."],
          ["Track & succeed", "Every application in one place, so you stay organised and in control."],
        ].map(([t, d]) => (
          <div key={t} className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
            <div className="mb-2 h-1 w-10 rounded" style={{ background: GOLD }} />
            <h3 className="font-bold" style={{ color: NAVY }}>{t}</h3>
            <p className="mt-1 text-sm text-gray-600">{d}</p>
          </div>
        ))}
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-6xl px-4 py-6">
        <h2 className="text-center text-2xl font-bold" style={{ color: NAVY }}>How it works</h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-4">
          {[
            ["01", "Create your profile", "Add your details and upload your CV — once."],
            ["02", "Browse employers", "367+ JSE companies and SOEs, searchable by name or sector."],
            ["03", "Go direct", "Open each employer's official careers page in one click."],
            ["04", "Apply & track", "Tailor your CV, apply, and track every application."],
          ].map(([n, t, d]) => (
            <div key={n} className="rounded-2xl bg-white p-5 shadow-sm">
              <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg text-sm font-bold text-white" style={{ background: NAVY }}>{n}</div>
              <h3 className="font-semibold" style={{ color: NAVY }}>{t}</h3>
              <p className="mt-1 text-sm text-gray-600">{d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section className="mx-auto max-w-6xl px-4 py-12">
        <div className="rounded-3xl px-6 py-12 text-center" style={{ background: NAVY }}>
          <h2 className="text-3xl font-extrabold text-white">Built for you. Built to connect you to opportunities.</h2>
          <p className="mx-auto mt-3 max-w-xl text-blue-100">Your data stays safe. Your future stays yours. Anytime, anywhere, any device.</p>
          <Link href="/register" className="mt-6 inline-block rounded-xl px-8 py-3 font-bold text-black shadow-lg" style={{ background: GOLD }}>Get started today →</Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-8 text-sm text-gray-500">
        <span>© 2026 Sospana Sonke</span>
        <a href="/privacy.html" className="hover:text-gray-800">Privacy Policy</a>
      </footer>
    </div>
  );
}
