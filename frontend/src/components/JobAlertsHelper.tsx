"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { WhatsAppIcon } from "./WhatsAppChannel";
import { WHATSAPP_CHANNEL_URL } from "@/lib/social";
import { detectPortal } from "@/lib/portalGuide";

type Emp = { a: string; n: string; u: string };
type Track = { name: string; url: string; registered: boolean; alerts: boolean; note: string };
type Country = { slug: string; name: string; flag: string };

const KEY = "ss-job-alerts-v1";
const ACCENTS = ["#0B6575", "#B8432A", "#E2AE3C", "#1E7A47", "#07284C"];

// Bright 3D card: layered shadows + top highlight for depth; no motion needed.
const CARD =
  "rounded-xl border border-[#07284C]/10 bg-gradient-to-b from-white to-[#FFFBF3] shadow-[0_1px_0_rgba(255,255,255,0.9)_inset,0_1px_2px_rgba(7,40,76,0.08),0_8px_20px_-6px_rgba(7,40,76,0.18)]";
const BTN =
  "inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-semibold shadow-[0_1px_0_rgba(255,255,255,0.35)_inset,0_2px_0_rgba(7,40,76,0.25),0_4px_10px_-4px_rgba(7,40,76,0.35)] transition-transform hover:-translate-y-px active:translate-y-px focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#07284C] motion-reduce:transition-none motion-reduce:hover:translate-y-0";

const STEPS = [
  "Open the employer's official careers link below (it opens in a new tab). Check the web address is the employer's own site or its recruitment portal.",
  "Look for Register, Sign up or Create profile. Use your own email address and a strong password that only you know.",
  "Confirm your email if the site sends you a link, then fill in your profile and upload your CV if asked.",
  "Look for Job alerts, Saved searches or Talent community. Pick the job types and locations you want and switch alerts on.",
  "Come back here and tick Registered and Alerts on, and write your next step so you remember it.",
];

export default function JobAlertsHelper({ sa, countries }: { sa: Emp[]; countries: Country[] }) {
  const [country, setCountry] = useState("south-africa");
  const [list, setList] = useState<Emp[]>(sa);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState("");
  const [tracks, setTracks] = useState<Record<string, Track>>({});
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) setTracks(JSON.parse(raw));
    } catch {}
    setReady(true);
  }, []);
  useEffect(() => {
    if (ready) try { localStorage.setItem(KEY, JSON.stringify(tracks)); } catch {}
  }, [tracks, ready]);

  useEffect(() => {
    if (country === "south-africa") { setList(sa); return; }
    let live = true;
    setLoading(true);
    fetch(`/job-alerts/employers/${country}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((d: Emp[]) => live && setList(d))
      .catch(() => live && setList([]))
      .finally(() => live && setLoading(false));
    return () => { live = false; };
  }, [country, sa]);

  const results = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (s.length < 2) return [];
    return list.filter((e) => e.n.toLowerCase().includes(s) || e.a.toLowerCase().includes(s)).slice(0, 12);
  }, [q, list]);

  const picked = Object.entries(tracks);
  const done = picked.filter(([, t]) => t.registered && t.alerts).length;
  const steps = picked.reduce((s, [, t]) => s + (t.registered ? 1 : 0) + (t.alerts ? 1 : 0), 0);
  const pct = picked.length ? Math.round((steps / (picked.length * 2)) * 100) : 0;

  const add = (e: Emp) => setTracks((t) => (t[e.u] ? t : { ...t, [e.u]: { name: e.n, url: e.u, registered: false, alerts: false, note: "" } }));
  const upd = (u: string, p: Partial<Track>) => setTracks((t) => ({ ...t, [u]: { ...t[u], ...p } }));
  const del = (u: string) => setTracks((t) => { const n = { ...t }; delete n[u]; return n; });

  return (
    <main className="min-h-screen bg-[#FBF6EC] [color-scheme:light]">
      <div className="mx-auto max-w-5xl px-4 py-8 font-sans text-[#07284C] sm:px-6">
        <div className={`${CARD} mb-6 border-t-4 border-t-[#E2AE3C] p-5 sm:p-6`}>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">🔔 Job alerts helper</h1>
          <p className="mt-2 max-w-3xl text-base leading-relaxed text-slate-700">
            Pick employers you want to work for, open their official careers portal, register and switch on job alerts.
            Track your progress here. Free for everyone, no login needed.
          </p>
          <p className="mt-3 max-w-3xl rounded-md border border-[#0B6575]/25 bg-[#EEF6F7] px-3 py-2 text-sm text-[#07284C]">
            🔒 We never log in for you and never ask for your passwords. Your tracker is saved only in this browser on
            this device. You register directly on each employer&apos;s own site.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link href="/sa-careers" className={`${BTN} bg-[#07284C] text-white hover:bg-[#0B3A6B]`}>🇿🇦 SA careers pages</Link>
            <a href={WHATSAPP_CHANNEL_URL} target="_blank" rel="noopener noreferrer" className={`${BTN} bg-[#25D366] text-[#07284C] hover:bg-[#1EBE5A]`}>
              <WhatsAppIcon className="h-4 w-4" /> Join our WhatsApp channel
            </a>
          </div>
        </div>

        <div role="alert" className={`${CARD} mb-6 border-l-[6px] border-l-[#B8432A] bg-[#FBF0EC] p-4 sm:p-5`}>
          <p className="text-base font-bold text-[#8A2F1C]">⚠️ Scam warning</p>
          <p className="mt-1 text-sm leading-relaxed text-[#07284C]">
            Real employers never charge fees for jobs, applications, interviews, training or job alerts. Never pay
            anyone to get a job, and never share your passwords, OTPs or banking details. Only use the official links.
          </p>
        </div>

        <section className={`${CARD} mb-6 border-l-[6px] border-l-[#0B6575] p-4 sm:p-5`} aria-labelledby="find">
          <h2 id="find" className="text-lg font-semibold">1. Find an employer</h2>
          <div className="mt-3 flex flex-col gap-3 sm:flex-row">
            <label className="flex flex-col text-sm font-medium sm:w-56">
              Country
              <select value={country} onChange={(e) => { setCountry(e.target.value); setQ(""); }} className="mt-1 rounded-md border border-[#07284C]/25 bg-white px-3 py-2 text-base">
                <option value="south-africa">🇿🇦 South Africa</option>
                {countries.map((c) => <option key={c.slug} value={c.slug}>{c.flag} {c.name}</option>)}
              </select>
            </label>
            <label className="flex flex-1 flex-col text-sm font-medium">
              Employer name
              <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Type at least 2 letters, e.g. Eskom" className="mt-1 rounded-md border border-[#07284C]/25 bg-white px-3 py-2 text-base" />
            </label>
          </div>
          <p className="mt-2 text-xs text-slate-600" aria-live="polite">
            {loading ? "Loading employers…" : `${list.length} employers in the directory for this country.`}
          </p>
          {results.length > 0 && (
            <ul className="mt-3 grid gap-2 sm:grid-cols-2">
              {results.map((e) => (
                <li key={e.u}>
                  <button type="button" onClick={() => add(e)} disabled={!!tracks[e.u]} className="w-full rounded-md border border-[#07284C]/15 bg-white px-3 py-2 text-left shadow-sm hover:border-[#0B6575] disabled:opacity-60">
                    <span className="block font-semibold">{e.n}</span>
                    <span className="block truncate text-xs text-slate-600">{tracks[e.u] ? "✓ Added to your tracker" : "+ Add to my tracker"}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {q.trim().length >= 2 && results.length === 0 && !loading && <p className="mt-3 text-sm text-slate-700">No employer with that name in the directory yet.</p>}
        </section>

        <section className={`${CARD} mb-6 p-4 sm:p-5`} aria-labelledby="progress">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 id="progress" className="text-lg font-semibold">2. Your tracker</h2>
            <span className="rounded-full bg-[#1E7A47] px-3 py-0.5 text-sm font-semibold text-white tabular-nums">{done} of {picked.length} fully set up</span>
          </div>
          <div className="mt-3 h-3 overflow-hidden rounded-full bg-[#07284C]/10 shadow-inner" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Overall progress">
            <div className="h-full rounded-full bg-gradient-to-r from-[#0B6575] via-[#1E7A47] to-[#E2AE3C] transition-[width] motion-reduce:transition-none" style={{ width: `${pct}%` }} />
          </div>
          {picked.length === 0 && <p className="mt-3 text-sm text-slate-700">Search above and add employers to start.</p>}
        </section>

        <div className="space-y-4">
          {picked.map(([u, t], i) => {
            const portal = detectPortal(u);
            const acc = ACCENTS[i % ACCENTS.length];
            return (
              <article key={u} className={`${CARD} border-l-[6px] p-4 sm:p-5`} style={{ borderLeftColor: acc }}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <h3 className="text-lg font-semibold">{t.name}</h3>
                  <button type="button" onClick={() => del(u)} className="text-sm text-slate-600 underline hover:text-[#B8432A]">Remove</button>
                </div>
                <a href={u} target="_blank" rel="noopener noreferrer" className={`${BTN} mt-3 bg-[#B8432A] text-white hover:bg-[#9A3722]`}>
                  Open official careers page ↗
                </a>
                <p className="mt-1 break-all text-xs text-slate-600">{u}</p>
                <div className="mt-4 flex flex-wrap gap-4">
                  <label className="inline-flex items-center gap-2 text-sm font-medium">
                    <input type="checkbox" className="h-5 w-5 accent-[#1E7A47]" checked={t.registered} onChange={(e) => upd(u, { registered: e.target.checked })} /> Registered
                  </label>
                  <label className="inline-flex items-center gap-2 text-sm font-medium">
                    <input type="checkbox" className="h-5 w-5 accent-[#1E7A47]" checked={t.alerts} onChange={(e) => upd(u, { alerts: e.target.checked })} /> Alerts on
                  </label>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${t.registered && t.alerts ? "bg-[#1E7A47] text-white" : "bg-[#E2AE3C] text-[#07284C]"}`}>
                    {t.registered && t.alerts ? "✓ Done" : t.registered ? "Next: switch on alerts" : "Next: register"}
                  </span>
                </div>
                <label className="mt-3 block text-sm font-medium">
                  Next step note
                  <input type="text" value={t.note} maxLength={200} onChange={(e) => upd(u, { note: e.target.value })} placeholder="e.g. Upload CV, confirm email" className="mt-1 w-full rounded-md border border-[#07284C]/25 bg-white px-3 py-2 text-base" />
                </label>
                <details className="mt-3">
                  <summary className="cursor-pointer text-sm font-semibold text-[#0B6575]">How to register and switch on alerts</summary>
                  <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-slate-700">
                    {STEPS.map((s) => <li key={s}>{s}</li>)}
                  </ol>
                  {portal && (
                    <div className="mt-3 rounded-md bg-[#FDF7E7] px-3 py-2 text-sm">
                      <p className="font-semibold">This looks like a {portal.name} portal</p>
                      <ul className="mt-1 list-disc pl-5 text-slate-700">{portal.notes.map((n) => <li key={n}>{n}</li>)}</ul>
                      <p className="mt-1 text-xs text-slate-600">Every employer sets up its portal differently, so button names may vary.</p>
                    </div>
                  )}
                  <p className="mt-2 text-xs text-slate-600">Some employers only post adverts on their site and have no account or alerts. If so, bookmark the page and check it weekly.</p>
                </details>
              </article>
            );
          })}
        </div>
      </div>
    </main>
  );
}
