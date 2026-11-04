import type { Metadata } from "next";
import Link from "next/link";
import data from "@/data/opportunitiesToday.json";
import OpportunitiesTodayLink from "@/components/OpportunitiesTodayLink";
import JobAlertsLink from "@/components/JobAlertsLink";
import CompanyPicker from "@/components/CompanyPicker";
import { HeroMap, ExploreMap, type ProvinceRow } from "@/components/home2/ProvinceMap";
import { MiniBars, MiniLine, MiniStack } from "@/components/home2/MiniCharts";
import { GHS, MYPE, NATIONAL, PROVINCE_OFFICIAL, QLFS, READING, type Source } from "@/data/officialStats";
import { PROVINCES, provinceOf } from "@/lib/province";

// Static data only (no database/backend). Re-rendered hourly so closed posts drop off.
export const revalidate = 3600;

export const metadata: Metadata = {
  title: "Sospana Sonke – Research • Opportunity • Impact",
  description:
    "Understand South Africa with official Stats SA figures, explore each province, and find open posts checked on employers' official careers pages. Free, no login.",
};

type Post = { employer: string; title: string; location: string | null; closingDate: string | null; url: string; category?: string };

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const fmtDate = (iso: string) => {
  const [y, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
};
const todaySA = () => new Date(Date.now() + 2 * 3600 * 1000).toISOString().slice(0, 10);

const CARD = "rounded-3xl border border-white/80 bg-white/85 shadow-[0_22px_44px_-26px_rgba(31,35,40,0.35),inset_0_1px_0_rgba(255,255,255,0.9)] backdrop-blur";
const FOCUS = "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0B6575]";

function SourceNote({ s, className = "" }: { s: Source; className?: string }) {
  return (
    <p className={`text-[11px] leading-snug text-[#4A4F57] ${className}`}>
      Source:{" "}
      <a href={s.url} target="_blank" rel="noopener noreferrer" className="underline hover:text-[#1F2328]">
        {s.label}
      </a>
      , {s.period}
    </p>
  );
}

const CAT_TAG: Record<string, { label: string; cls: string }> = {
  "Government departments": { label: "Government", cls: "bg-[#EEF6F7] text-[#0B6575]" },
  "State-owned companies": { label: "State-owned", cls: "bg-[#EDF6F0] text-[#1E6B40]" },
  Universities: { label: "Study & work", cls: "bg-[#FDF3DC] text-[#7A5200]" },
  Colleges: { label: "Study & work", cls: "bg-[#FDF3DC] text-[#7A5200]" },
  SETAs: { label: "Skills", cls: "bg-[#FDF3DC] text-[#7A5200]" },
};
const tagFor = (c?: string) => CAT_TAG[c ?? ""] ?? { label: "Career", cls: "bg-[#FBF0EC] text-[#9A3722]" };

export default function HomePage() {
  const today = todaySA();
  const { date, posts: all } = data as { date: string; posts: Post[] };
  const posts = all.filter((p) => !p.closingDate || p.closingDate >= today);
  const latest = posts
    .filter((p) => p.closingDate)
    .sort((a, b) => (a.closingDate! < b.closingDate! ? -1 : a.closingDate! > b.closingDate! ? 1 : 0))
    .slice(0, 5);

  const byProv = new Map<string, { opps: number; employers: Set<string> }>();
  for (const p of posts) {
    const code = provinceOf(p.location);
    if (!code) continue;
    const r = byProv.get(code) ?? { opps: 0, employers: new Set<string>() };
    r.opps += 1;
    r.employers.add(p.employer);
    byProv.set(code, r);
  }
  const rows: ProvinceRow[] = PROVINCES.map((p) => ({
    code: p.code,
    name: p.name,
    population: PROVINCE_OFFICIAL[p.code].population,
    unemployment: PROVINCE_OFFICIAL[p.code].unemployment,
    opps: byProv.get(p.code)?.opps ?? 0,
    employers: byProv.get(p.code)?.employers.size ?? 0,
  }));
  const employerCount = new Set(posts.map((p) => p.employer)).size;

  return (
    <div className="ss-home -mx-4 -my-6 overflow-hidden bg-[#FBF6EC] text-[#1F2328]">
      {/* HERO */}
      <section className="relative isolate px-4 pb-10 pt-8 sm:pt-12">
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(60%_60%_at_85%_20%,#FDE3C8_0%,transparent_70%),radial-gradient(50%_50%_at_10%_10%,#DDF0EE_0%,transparent_70%),linear-gradient(180deg,#FFFDF8_0%,#FBF6EC_100%)]" />
        <div className="mx-auto grid max-w-6xl grid-cols-[minmax(0,1fr)] items-center gap-10 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
          <div className="min-w-0">
            <p className="inline-flex items-center gap-2 rounded-full border border-[#E2AE3C]/60 bg-white/80 px-3 py-1 text-xs font-bold uppercase tracking-[0.14em] text-[#7A5200] shadow-sm">
              Sospana Sonke – Research • Opportunity • Impact
            </p>
            <h1 className="mt-5 text-4xl font-extrabold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
              Understand South Africa.
              <br />
              <span className="bg-gradient-to-r from-[#B8432A] to-[#9A5A00] bg-clip-text text-transparent">Shape what comes next.</span>
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-[#3A3F47]">
              Official figures on jobs, people and services, every province on one map, and open posts checked on
              employers&apos; own careers pages. Free, no login.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link href="/opportunities-today" className={`inline-flex items-center gap-2 rounded-full bg-[#B8432A] px-6 py-3 text-base font-bold text-white shadow-[0_12px_24px_-10px_rgba(184,67,42,0.7)] transition hover:-translate-y-0.5 hover:bg-[#9A3722] motion-reduce:transition-none ${FOCUS}`}>
                Explore opportunities →
              </Link>
              <Link href="/sa-careers" className={`inline-flex items-center gap-2 rounded-full border-2 border-[#0B6575] bg-white px-6 py-3 text-base font-bold text-[#0B6575] shadow-sm transition hover:-translate-y-0.5 hover:bg-[#EEF6F7] motion-reduce:transition-none ${FOCUS}`}>
                Explore careers →
              </Link>
            </div>
            <a
              href="/game/play.html"
              className={`group mt-6 flex max-w-xl items-center gap-4 rounded-2xl border-2 border-[#E2AE3C] bg-gradient-to-r from-[#FFF8EC] to-white p-4 shadow-md transition hover:-translate-y-0.5 hover:shadow-lg motion-reduce:transition-none ${FOCUS}`}
            >
              <span aria-hidden="true" className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#0B6575] text-2xl shadow-inner">🎮</span>
              <span className="min-w-0 flex-1">
                <span className="block text-lg font-extrabold">Play Gauteng Hustle Run</span>
                <span className="block text-sm text-[#4A4F57]">Free game. Run, collect coins, dodge obstacles. Works offline.</span>
              </span>
              <span className="shrink-0 rounded-full bg-[#B8432A] px-4 py-2 text-sm font-bold text-white group-hover:bg-[#9A3722]">Play now</span>
            </a>
          </div>

          <div className="relative min-w-0">
            <div className={`${CARD} relative p-4 sm:p-6`}>
              <HeroMap />
              <p className="mt-2 text-center text-xs text-[#4A4F57]">Tap a province to see its figures.</p>
            </div>
            <div className="mt-4 grid grid-cols-1 gap-2 min-[440px]:grid-cols-3 sm:gap-3">
              {[
                { v: `${NATIONAL.populationMillions.toFixed(2)}M`, l: "People", p: "mid-2026", s: MYPE },
                { v: `${NATIONAL.unemploymentRate.toFixed(1)}%`, l: "Unemployment rate", p: "Q2 2026", s: QLFS },
                { v: `${NATIONAL.electricity[1].value.toFixed(1)}%`, l: "Homes on mains electricity", p: "2025", s: GHS },
              ].map((c) => (
                <div key={c.l} className="rounded-2xl border border-white/80 bg-white/90 p-3 shadow-[0_14px_28px_-18px_rgba(31,35,40,0.45)] backdrop-blur">
                  <p className="text-xl font-extrabold tabular-nums sm:text-2xl">{c.v}</p>
                  <p className="text-xs font-semibold leading-tight text-[#3A3F47]">{c.l}</p>
                  <p className="mt-1 text-[10px] leading-tight text-[#4A4F57]">
                    <a href={c.s.url} target="_blank" rel="noopener noreferrer" className="underline">Stats SA</a>, {c.p}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* DEVELOPMENT DASHBOARD */}
      <section aria-labelledby="dash-h" className="px-4 pb-12">
        <div className="mx-auto max-w-6xl">
          <h2 id="dash-h" className="sr-only">Development dashboard</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className={`${CARD} flex flex-col p-5`}>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="flex items-center gap-2 text-sm font-bold text-[#0B6575]"><span aria-hidden="true" className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#EEF6F7]">💼</span>Jobs &amp; Skills</p>
                  <p className="mt-3 text-3xl font-extrabold tabular-nums">{(NATIONAL.employedThousands / 1000).toFixed(1)}M</p>
                  <p className="text-sm text-[#3A3F47]">people employed (15–64)</p>
                </div>
                <MiniLine points={NATIONAL.unemploymentTrend} color="#0B6575" label={`Official unemployment rate: ${NATIONAL.unemploymentTrend.map((p) => `${p.label} ${p.value}%`).join(", ")}`} />
              </div>
              <p className="mt-2 text-xs text-[#3A3F47]">Chart: unemployment rate {NATIONAL.unemploymentTrend.map((p) => `${p.value}%`).join(" → ")} ({NATIONAL.unemploymentTrend[0].label}–{NATIONAL.unemploymentTrend[2].label})</p>
              <SourceNote s={QLFS} className="mt-auto pt-3" />
            </div>
            <div className={`${CARD} flex flex-col p-5`}>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="flex items-center gap-2 text-sm font-bold text-[#1E6B40]"><span aria-hidden="true" className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#EDF6F0]">🏠</span>Housing</p>
                  <p className="mt-3 text-3xl font-extrabold tabular-nums">{NATIONAL.dwellings.formal}%</p>
                  <p className="text-sm text-[#3A3F47]">of households in formal dwellings</p>
                </div>
                <MiniStack
                  label={`Households by dwelling: formal ${NATIONAL.dwellings.formal}%, informal ${NATIONAL.dwellings.informal}%, traditional ${NATIONAL.dwellings.traditional}%`}
                  parts={[
                    { label: "Formal", value: NATIONAL.dwellings.formal, color: "#1E7A47" },
                    { label: "Informal", value: NATIONAL.dwellings.informal, color: "#E2AE3C" },
                    { label: "Traditional", value: NATIONAL.dwellings.traditional, color: "#B8432A" },
                  ]}
                />
              </div>
              <p className="mt-2 text-xs text-[#3A3F47]">Chart: formal {NATIONAL.dwellings.formal}% · informal {NATIONAL.dwellings.informal}% · traditional {NATIONAL.dwellings.traditional}%</p>
              <SourceNote s={GHS} className="mt-auto pt-3" />
            </div>
            <div className={`${CARD} flex flex-col p-5`}>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="flex items-center gap-2 text-sm font-bold text-[#6B3FA0]"><span aria-hidden="true" className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#F3EEFA]">⚡</span>Public Services</p>
                  <p className="mt-3 text-3xl font-extrabold tabular-nums">{NATIONAL.electricity[1].value}%</p>
                  <p className="text-sm text-[#3A3F47]">of households on mains electricity</p>
                </div>
                <MiniBars bars={NATIONAL.electricity} color="#6B3FA0" label={`Households on mains electricity: ${NATIONAL.electricity.map((p) => `${p.label} ${p.value}%`).join(", ")}`} />
              </div>
              <p className="mt-2 text-xs text-[#3A3F47]">Chart: {NATIONAL.electricity.map((p) => `${p.label} ${p.value}%`).join(" → ")}</p>
              <SourceNote s={GHS} className="mt-auto pt-3" />
            </div>
            <div className={`${CARD} flex flex-col p-5`}>
              <p className="flex items-center gap-2 text-sm font-bold text-[#9A3722]"><span aria-hidden="true" className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#FBF0EC]">🤝</span>Community Projects</p>
              <p className="mt-3 inline-flex w-fit rounded-full bg-[#FDF3DC] px-3 py-1 text-sm font-bold text-[#7A5200]">Coming soon</p>
              <p className="mt-2 text-sm text-[#3A3F47]">
                We have no verified source for community projects yet, so we show no number. When one is ready, it will be listed here with its source.
              </p>
              <Link href="/stats" className={`mt-auto pt-3 text-sm font-semibold text-[#0B6575] underline ${FOCUS}`}>See site stats →</Link>
            </div>
          </div>
        </div>
      </section>

      {/* OFFICIAL REPORTS + LATEST OPPORTUNITIES */}
      <section className="px-4 pb-12">
        <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
          <div>
            <div className="mb-3 flex items-end justify-between gap-3">
              <h2 className="border-l-4 border-[#E2AE3C] pl-3 text-2xl font-extrabold tracking-tight">Featured research</h2>
              <Link href="/data" className="text-sm font-semibold text-[#0B6575] underline">Labour data →</Link>
            </div>
            <p className="mb-3 text-sm text-[#3A3F47]">Our own research is coming soon. Until then, read the official Stats SA reports behind the figures on this page.</p>
            <ul className="grid gap-4 sm:grid-cols-3">
              {READING.map((r, i) => (
                <li key={r.title}>
                  <a href={r.source.url} target="_blank" rel="noopener noreferrer" className={`group flex h-full flex-col overflow-hidden ${CARD} transition hover:-translate-y-1 motion-reduce:transition-none ${FOCUS}`}>
                    <span aria-hidden="true" className={`block h-20 ${["bg-gradient-to-br from-[#DDF0EE] to-[#BFE3E0]", "bg-gradient-to-br from-[#FDE3C8] to-[#F6C9B8]", "bg-gradient-to-br from-[#FBEBD0] to-[#F8DFA3]"][i]}`} />
                    <span className="flex flex-1 flex-col p-4">
                      <span className="text-base font-extrabold leading-snug">{r.title}</span>
                      <span className="mt-1 text-sm text-[#3A3F47]">{r.blurb}</span>
                      <span className="mt-auto pt-3 text-[11px] text-[#4A4F57]">{r.source.label}, {r.source.period} (PDF)</span>
                    </span>
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div className={`${CARD} p-5`}>
            <div className="mb-3 flex items-end justify-between gap-3">
              <h2 className="border-l-4 border-[#B8432A] pl-3 text-2xl font-extrabold tracking-tight">Latest opportunities</h2>
              <Link href="/opportunities-today" className="text-sm font-semibold text-[#0B6575] underline">View all →</Link>
            </div>
            <p className="mb-3 text-xs text-[#4A4F57]">Closing soonest, from {posts.length.toLocaleString("en-ZA").replace(/,/g, " ")} open posts at {employerCount} employers (list of {fmtDate(date)}). Apply only on the official link.</p>
            <ul className="divide-y divide-[#1F2328]/10">
              {latest.map((p) => {
                const t = tagFor(p.category);
                return (
                  <li key={p.url + p.title}>
                    <a href={p.url} target="_blank" rel="noopener noreferrer" className={`flex items-start gap-3 rounded-xl px-2 py-3 hover:bg-[#FBF6EC] ${FOCUS}`}>
                      <span className="min-w-0 flex-1">
                        <span className="block font-bold leading-snug">{p.title}</span>
                        <span className="block text-sm text-[#3A3F47]">{p.employer}{p.location ? ` · ${p.location}` : ""}</span>
                        <span className="block text-sm font-semibold text-[#9A3722]">Closes {fmtDate(p.closingDate!)}</span>
                      </span>
                      <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-bold ${t.cls}`}>{t.label}</span>
                    </a>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      </section>

      {/* EXPLORE SOUTH AFRICA */}
      <section id="explore" aria-labelledby="explore-h" className="scroll-mt-24 bg-gradient-to-b from-[#FBF6EC] via-[#F3F8F6] to-[#FBF6EC] px-4 py-12">
        <div className="mx-auto max-w-6xl">
          <h2 id="explore-h" className="border-l-4 border-[#0B6575] pl-3 text-2xl font-extrabold tracking-tight sm:text-3xl">Explore South Africa</h2>
          <p className="mb-6 mt-2 max-w-2xl text-[#3A3F47]">Choose a province on the map or in the list to see its people, unemployment rate and the open posts we list there.</p>
          <ExploreMap
            rows={rows}
            sources={{ mype: `Stats SA P0302, ${MYPE.period}`, qlfs: `Stats SA QLFS, ${QLFS.period}`, mypeUrl: MYPE.url, qlfsUrl: QLFS.url, oppsDate: fmtDate(date) }}
          />
        </div>
      </section>

      {/* TOOLS: company picker, opportunities, alerts */}
      <section className="px-4 py-12">
        <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-2">
          <CompanyPicker />
          <div className="flex flex-col gap-4">
            <OpportunitiesTodayLink />
            <JobAlertsLink />
          </div>
        </div>
      </section>

      {/* CLOSING CARD */}
      <section className="px-4 pb-12">
        <div className="relative mx-auto max-w-6xl overflow-hidden rounded-[2rem] border border-white/80 bg-gradient-to-br from-[#FFF4E2] via-white to-[#E6F3F1] p-8 shadow-[0_30px_60px_-30px_rgba(31,35,40,0.4)] sm:p-10">
          <div aria-hidden="true" className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-[#F8DFA3]/60 blur-3xl" />
          <h2 className="relative text-3xl font-extrabold tracking-tight">Building a Better South Africa</h2>
          <p className="relative mt-3 max-w-2xl text-lg text-[#3A3F47]">
            Together, through knowledge and honest information, we can find opportunities and make better choices for our communities.
          </p>
          <ul className="relative mt-6 flex flex-wrap gap-3 text-sm font-bold">
            <li className="rounded-full bg-white px-4 py-2 shadow-sm">💡 Learn</li>
            <li className="rounded-full bg-white px-4 py-2 shadow-sm">🤝 Collaborate</li>
            <li className="rounded-full bg-white px-4 py-2 shadow-sm">📈 Thrive</li>
          </ul>
        </div>
      </section>
    </div>
  );
}
