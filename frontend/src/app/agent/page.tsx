"use client";

/**
 * Sospana Sonke Career Agent (blueprint sections 1, 7, 8, 10, 16–21).
 *
 * A conversational front door over the platform's existing, deterministic
 * matching engine and live vacancy index. Everything shown here comes from real
 * endpoints — `/matches/run`, `/matches`, `/matches/{id}`, `/vacancies`,
 * `/profile`, `/companies`. The agent never invents a vacancy, employer, salary,
 * closing date or match score, and never tells a candidate they are eligible
 * when the engine flags a hard requirement as unmet. When the live index has
 * nothing to show, it says so plainly and points to the employer directory.
 *
 * The "understanding" here is deterministic keyword/intent parsing done in the
 * browser (no hidden LLM claim) — it maps a plain-English request to the same
 * structured search + scoring the rest of the app already does.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Card, Button, Badge, Alert, Spinner, Input } from "@/components/ui";
import type { Match, MatchDetail, Vacancy, Company } from "@/lib/types";

/* ------------------------------------------------------------------ */
/* Domain vocab (mirrors backend app/common/vocab.py, kept in sync by  */
/* hand — used for deterministic query understanding & career discovery)*/
/* ------------------------------------------------------------------ */

const SA_PROVINCES = [
  "gauteng", "limpopo", "mpumalanga", "north west", "free state",
  "kwazulu-natal", "kwazulu natal", "kzn", "eastern cape", "western cape",
  "northern cape",
];

// Common SA/African place hints so "jobs in Vereeniging" resolves a location
// filter even when it isn't a province.
const PLACE_HINTS = [
  ...SA_PROVINCES,
  "johannesburg", "joburg", "pretoria", "tshwane", "vereeniging", "vanderbijlpark",
  "sebokeng", "evaton", "sedibeng", "cape town", "durban", "ethekwini",
  "port elizabeth", "gqeberha", "bloemfontein", "polokwane", "nelspruit",
  "mbombela", "kimberley", "rustenburg", "east london", "sasolburg", "secunda",
  "south africa", "botswana", "namibia", "zambia", "zimbabwe", "mozambique",
  "kenya", "nigeria", "ghana", "eswatini", "lesotho",
];

// Qualification level keywords (ordered low→high), aligned with EDUCATION_RANK.
const QUALIFICATION_LEVELS: { label: string; keys: string[] }[] = [
  { label: "Matric / Grade 12", keys: ["matric", "grade 12"] },
  { label: "Certificate", keys: ["certificate", "national certificate"] },
  { label: "Diploma", keys: ["diploma", "national diploma"] },
  { label: "Degree", keys: ["degree", "bachelor", "bcom", "bsc", "b.com", "b.sc"] },
  { label: "Honours", keys: ["honours", "honors"] },
  { label: "Postgraduate Diploma", keys: ["postgraduate diploma", "pgdip", "postgraduate"] },
  { label: "Master's", keys: ["master", "mba", "msc", "meng"] },
  { label: "Doctorate", keys: ["phd", "doctorate", "doctoral"] },
];

const WORK_MODES = ["remote", "hybrid", "on-site", "on site", "onsite"];

const EMPLOYMENT_TYPES = [
  "permanent", "contract", "temporary", "temp", "internship", "intern",
  "learnership", "graduate programme", "graduate program", "graduate",
];

// Adjacent job families for career discovery + synonym expansion. Each row is a
// cluster of roles that tend to draw on overlapping qualifications/experience —
// used to suggest related searches, NEVER to claim the candidate qualifies.
const ROLE_FAMILIES: string[][] = [
  ["operations manager", "operations management", "operations supervisor", "operations coordinator", "operations officer", "plant manager", "production manager"],
  ["process controller", "process operator", "plant operator", "process technician", "production operator", "control room operator"],
  ["water treatment", "wastewater", "water quality", "water process controller", "water treatment technician", "water care", "purification"],
  ["production supervisor", "production planner", "shift supervisor", "manufacturing supervisor", "foreman"],
  ["quality controller", "quality officer", "quality assurance", "qa officer", "quality technician", "quality inspector"],
  ["laboratory technician", "lab technician", "laboratory analyst", "microbiologist", "lab assistant", "chemist"],
  ["maintenance technician", "maintenance planner", "millwright", "fitter", "artisan"],
  ["supply chain", "logistics", "warehouse", "procurement", "inventory controller", "stock controller"],
  ["administrator", "admin clerk", "office administrator", "data capturer", "receptionist", "personal assistant"],
  ["accountant", "bookkeeper", "finance clerk", "creditors clerk", "debtors clerk", "financial officer"],
  ["human resources", "hr officer", "hr administrator", "recruitment", "payroll administrator"],
  ["software developer", "software engineer", "web developer", "data analyst", "it technician", "systems administrator"],
  ["civil engineer", "mechanical engineer", "electrical engineer", "engineering technician", "technologist"],
  ["sales representative", "sales consultant", "account manager", "customer service", "call centre agent"],
  ["safety officer", "she officer", "health and safety", "environmental officer", "sheq"],
  ["driver", "code 10", "code 14", "delivery driver", "forklift operator"],
  ["general worker", "cleaner", "picker packer", "machine operator", "security officer"],
];

const STOPWORDS = new Set([
  "find", "show", "me", "some", "any", "jobs", "job", "vacancy", "vacancies",
  "posts", "positions", "position", "roles", "role", "work", "for", "a", "an",
  "the", "in", "at", "near", "around", "with", "and", "or", "of", "to", "that",
  "i", "can", "apply", "am", "qualified", "please", "looking", "want", "need",
  "requiring", "require", "requires", "preferably", "least", "years", "year",
  "experience", "suitable", "someone", "who", "has", "have", "my", "on", "site",
  "remote", "hybrid", "permanent", "contract", "temporary", "salary", "minimum",
  "maximum", "province", "gauteng", "limpopo", "mpumalanga", "cape", "north",
  "west", "free", "state", "eastern", "western", "northern", "kwazulu", "natal",
]);

/* ------------------------------------------------------------------ */
/* Intent parsing                                                      */
/* ------------------------------------------------------------------ */

type Mode = "apply" | "almost" | "discovery" | "search";

interface ParsedFilters {
  location?: string;
  qualification?: string;
  minYears?: number;
  workMode?: string;
  employmentType?: string;
  minSalary?: number;
}

interface ParsedQuery {
  mode: Mode;
  keyword: string;
  synonyms: string[];
  filters: ParsedFilters;
}

function firstMatch(text: string, options: string[]): string | undefined {
  for (const o of options) if (text.includes(o)) return o;
  return undefined;
}

function synonymsFor(term: string): string[] {
  if (!term) return [];
  const t = term.toLowerCase();
  const out = new Set<string>();
  for (const fam of ROLE_FAMILIES) {
    if (fam.some((r) => t.includes(r) || r.includes(t))) {
      fam.forEach((r) => out.add(r));
    }
  }
  out.delete(t);
  return Array.from(out).slice(0, 6);
}

function classifyIntent(raw: string): ParsedQuery {
  const text = raw.toLowerCase().trim();
  const filters: ParsedFilters = {};

  const place = firstMatch(text, PLACE_HINTS);
  if (place) filters.location = place;

  for (const q of QUALIFICATION_LEVELS) {
    if (q.keys.some((k) => text.includes(k))) {
      filters.qualification = q.label;
      break;
    }
  }

  const yearsM = text.match(/(\d+)\s*\+?\s*(?:years?|yrs?)/);
  if (yearsM) filters.minYears = parseInt(yearsM[1], 10);

  const wm = firstMatch(text, WORK_MODES);
  if (wm) filters.workMode = wm.replace("on site", "on-site").replace("onsite", "on-site");

  const et = firstMatch(text, EMPLOYMENT_TYPES);
  if (et) filters.employmentType = et;

  const salM = text.match(/r\s?([\d][\d\s,]{2,})/);
  if (salM) {
    const n = parseInt(salM[1].replace(/[\s,]/g, ""), 10);
    if (!Number.isNaN(n) && n >= 100) filters.minSalary = n;
  }

  // Intent
  let mode: Mode = "search";
  if (/\balmost\b|\bnearly\b|close to qualif|stretch|develop into|grow into/.test(text)) {
    mode = "almost";
  } else if (/can i apply|jobs i can apply|apply for|eligible|i qualify|qualify for/.test(text)) {
    mode = "apply";
  } else if (/\bdiscover\b|what (jobs|roles|careers)|related roles|adjacent|career (path|options|ideas)|suitable for (me|someone)/.test(text)) {
    mode = "discovery";
  }

  // Keyword: strip stopwords + filter tokens, keep meaningful role words.
  const tokens = text
    .replace(/[^a-z0-9\s+/-]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length > 1 && !STOPWORDS.has(w));
  const keyword = tokens.join(" ").trim();

  return { mode, keyword, synonyms: synonymsFor(keyword), filters };
}

/* ------------------------------------------------------------------ */
/* Closing-date intelligence (blueprint section 14)                    */
/* ------------------------------------------------------------------ */

function closingStatus(closing: string | null): { label: string; cls: string } {
  if (!closing) return { label: "Closing date not provided", cls: "bg-gray-100 text-gray-500" };
  const d = new Date(closing + "T00:00:00");
  if (Number.isNaN(d.getTime())) return { label: "Closing date not provided", cls: "bg-gray-100 text-gray-500" };
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const days = Math.round((d.getTime() - today.getTime()) / 86400000);
  if (days < 0) return { label: "Closed", cls: "bg-gray-200 text-gray-600" };
  if (days === 0) return { label: "Closing today", cls: "bg-coral/15 text-coral" };
  if (days <= 2) return { label: `Closes in ${days} day${days === 1 ? "" : "s"}`, cls: "bg-coral/15 text-coral" };
  if (days <= 7) return { label: `Closes in ${days} days`, cls: "bg-gold/20 text-[#8a6d00]" };
  return { label: `Open · closes ${closing}`, cls: "bg-green-100 text-green-700" };
}

/* ------------------------------------------------------------------ */
/* Eligibility phrasing (blueprint sections 9 & 10 — never overclaim)  */
/* ------------------------------------------------------------------ */

function eligibility(m: Match): { label: string; cls: string } {
  if (!m.hard_ok) return { label: "Requirement not confirmed", cls: "text-coral" };
  if (m.decision === "APPLY") return { label: "You appear to meet the key requirements", cls: "text-green-700" };
  if (m.decision === "REVIEW") return { label: "Likely match — worth reviewing", cls: "text-[#8a6d00]" };
  return { label: "Does not appear to meet the requirements", cls: "text-gray-500" };
}

function scoreColor(score: number): string {
  if (score >= 85) return "text-green-700";
  if (score >= 75) return "text-teal-700";
  if (score >= 65) return "text-[#8a6d00]";
  return "text-gray-500";
}

/* ------------------------------------------------------------------ */
/* Chat message model                                                  */
/* ------------------------------------------------------------------ */

interface AgentTurn {
  id: string;
  role: "user" | "agent";
  text: string;
  matches?: Match[];        // personalized, scored
  vacancies?: VacancyCardData[];
  roleChips?: string[];     // clickable adjacent-role suggestions
  cta?: { label: string; href: string }[];
}

interface VacancyCardData {
  vacancy: Vacancy;
  employer: string | null;
  employerCareers: string | null;
}

let TURN_SEQ = 0;
const nextId = () => `t${Date.now()}_${TURN_SEQ++}`;

/* ================================================================== */

function AgentInner() {
  const { user } = useAuth();
  const [turns, setTurns] = useState<AgentTurn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  // Caches
  const companyMap = useRef<Map<string, Company> | null>(null);
  const matchDetailCache = useRef<Map<string, MatchDetail>>(new Map());
  const profile = useRef<ProfileLite | null>(null);
  const ranAllMatches = useRef(false);

  // Compare + save trays
  const [compare, setCompare] = useState<Match[]>([]);
  const [saved, setSaved] = useState<Record<string, Match>>({});
  const [showCompare, setShowCompare] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns, busy]);

  // Restore saved jobs (real app origin — localStorage is fine here).
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem("sospana_agent_saved");
      if (raw) setSaved(JSON.parse(raw));
    } catch { /* ignore */ }
  }, []);
  useEffect(() => {
    try { window.localStorage.setItem("sospana_agent_saved", JSON.stringify(saved)); } catch { /* ignore */ }
  }, [saved]);

  const pushAgent = useCallback((t: Omit<AgentTurn, "id" | "role">) => {
    setTurns((prev) => [...prev, { id: nextId(), role: "agent", ...t }]);
  }, []);

  async function ensureCompanies(): Promise<Map<string, Company>> {
    if (companyMap.current) return companyMap.current;
    const rows = await api.get<Company[]>("/companies?limit=5000");
    const m = new Map<string, Company>();
    rows.forEach((c) => m.set(c.id, c));
    companyMap.current = m;
    return m;
  }

  async function ensureProfile(): Promise<ProfileLite> {
    if (profile.current) return profile.current;
    const p = await api.get<ProfileLite>("/profile");
    profile.current = p;
    return p;
  }

  // Run the deterministic matching engine over the whole open index for this
  // user, once per session (idempotent server-side), then read the scored list.
  async function runAndGetMatches(): Promise<Match[]> {
    if (!ranAllMatches.current) {
      try { await api.post("/matches/run"); } catch { /* non-fatal: read whatever exists */ }
      ranAllMatches.current = true;
    }
    return api.get<Match[]>("/matches?limit=200");
  }

  /* ---- handlers ---- */

  async function handleApply() {
    const matches = await runAndGetMatches();
    const eligible = matches
      .filter((m) => m.hard_ok && (m.decision === "APPLY" || m.decision === "REVIEW"))
      .sort((a, b) => b.score - a.score);
    if (eligible.length === 0) {
      pushAgent({
        text:
          matches.length === 0
            ? "I ran your profile against the live vacancy index and didn't find scored vacancies yet. The index is still filling up for many employers — the fastest route right now is to browse employers' own careers pages directly and apply there. Completing your Profile also sharpens future matches."
            : "I couldn't find vacancies you clearly meet the requirements for yet. Have a look at 'Jobs I'm almost qualified for' to see roles you're close on, or browse employers directly.",
        cta: [
          { label: "Browse employers →", href: "/companies" },
          { label: "Complete my profile →", href: "/profile" },
        ],
      });
      return;
    }
    pushAgent({
      text: `I scored the open vacancy index against your profile and found ${eligible.length} you appear to meet the key requirements for. Ranked strongest first:`,
      matches: eligible.slice(0, 20),
    });
  }

  async function handleAlmost() {
    const matches = await runAndGetMatches();
    const almost = matches
      .filter((m) => (!m.hard_ok || m.band === "Possible" || m.band === "Weak") && m.score >= 45 && m.decision !== "DO_NOT_APPLY")
      .sort((a, b) => b.score - a.score);
    if (almost.length === 0) {
      pushAgent({
        text: "Nothing in the current index falls into the 'almost qualified' band for you right now. As more vacancies are indexed this will populate. In the meantime, browsing employers directly is the surest route.",
        cta: [{ label: "Browse employers →", href: "/companies" }],
      });
      return;
    }
    pushAgent({
      text: `These ${almost.length} roles are close matches where you're missing only one or two things — useful for career development. Expand 'Why' on any card to see exactly what's needed:`,
      matches: almost.slice(0, 15),
    });
  }

  async function handleDiscovery() {
    const p = await ensureProfile();
    const seeds: string[] = [];
    if (p.current_occupation) seeds.push(p.current_occupation);
    (p.desired_occupations || []).forEach((d) => seeds.push(d));
    if (user?.preferred_position) seeds.push(user.preferred_position);

    const related = new Set<string>();
    seeds.forEach((s) => synonymsFor(s.toLowerCase()).forEach((r) => related.add(titleCase(r))));
    // If we still have nothing (empty profile), offer a broad starter set.
    if (related.size === 0) {
      ["Process Controller", "Operations Officer", "Production Supervisor", "Quality Officer", "Laboratory Technician", "Administrator"].forEach((r) => related.add(r));
    }
    const chips = Array.from(related).slice(0, 12);
    pushAgent({
      text: seeds.length
        ? `Based on your profile (${seeds.slice(0, 3).join(", ")}), here are related job families you may be able to move into. Tap any one to search the live index for it — I'll be honest about what each role actually requires.`
        : "Your profile is light on preferred roles, so here are common starting points. Tap one to search — or add preferred roles on your Profile for sharper suggestions.",
      roleChips: chips,
      cta: seeds.length ? undefined : [{ label: "Add preferred roles →", href: "/profile" }],
    });
  }

  async function handleSearch(parsed: ParsedQuery) {
    if (!parsed.keyword) {
      pushAgent({
        text: "Tell me a job title or skill to search for — e.g. \"process controller\", \"water treatment diploma jobs in Gauteng\", or \"operations management, 5 years experience\".",
      });
      return;
    }
    const terms = [parsed.keyword, ...parsed.synonyms];
    const seen = new Set<string>();
    let vacs: Vacancy[] = [];
    for (const term of terms) {
      if (vacs.length >= 30) break;
      let batch: Vacancy[] = [];
      try {
        batch = await api.get<Vacancy[]>(`/vacancies?q=${encodeURIComponent(term)}&is_open=true&limit=50`);
      } catch { batch = []; }
      for (const v of batch) {
        if (!seen.has(v.id)) { seen.add(v.id); vacs.push(v); }
      }
    }

    // Apply client-side filters the /vacancies endpoint doesn't cover.
    const f = parsed.filters;
    vacs = vacs.filter((v) => {
      if (f.location && v.location && !v.location.toLowerCase().includes(f.location)) return false;
      if (f.workMode && v.work_mode && !v.work_mode.toLowerCase().includes(f.workMode.replace("-", ""))) {
        // work_mode stored as remote|hybrid|onsite
        if (!(f.workMode.includes(v.work_mode.toLowerCase()))) return false;
      }
      if (f.employmentType && v.employment_type && !v.employment_type.toLowerCase().includes(f.employmentType.replace("intern", "intern"))) return false;
      return true;
    });

    if (vacs.length === 0) {
      const chips = parsed.synonyms.map(titleCase).slice(0, 6);
      pushAgent({
        text: `I searched the live index for "${parsed.keyword}"${describeFilters(f)} and found no open, indexed vacancies matching right now. That usually means no employer's page has been indexed with that title yet — not that nothing exists. You can browse employers directly, or try a related role.`,
        roleChips: chips.length ? chips : undefined,
        cta: [{ label: "Browse employers →", href: "/companies" }],
      });
      return;
    }

    const cmap = await ensureCompanies();
    const cards: VacancyCardData[] = vacs.slice(0, 25).map((v) => {
      const c = cmap.get(v.company_id) || null;
      return { vacancy: v, employer: c?.company_name ?? null, employerCareers: c?.careers_url ?? null };
    });
    pushAgent({
      text: `Found ${vacs.length} open vacanc${vacs.length === 1 ? "y" : "ies"} for "${parsed.keyword}"${describeFilters(f)}. These are live directory results, not yet scored against your profile — tap "Score these against my profile" to rank them.`,
      vacancies: cards,
      cta: [{ label: "Score against my profile", href: "#score" }],
    });
  }

  async function submit(raw: string) {
    const text = raw.trim();
    if (!text || busy) return;
    setErr("");
    setInput("");
    setTurns((prev) => [...prev, { id: nextId(), role: "user", text }]);
    setBusy(true);
    try {
      const parsed = classifyIntent(text);
      if (parsed.mode === "apply") await handleApply();
      else if (parsed.mode === "almost") await handleAlmost();
      else if (parsed.mode === "discovery") await handleDiscovery();
      else await handleSearch(parsed);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Something went wrong.";
      setErr(msg);
      pushAgent({ text: `Sorry — I hit an error reaching the vacancy service (${msg}). Please try again in a moment.` });
    } finally {
      setBusy(false);
    }
  }

  function quick(label: string, text: string) {
    return (
      <button
        key={label}
        onClick={() => submit(text)}
        disabled={busy}
        className="rounded-full border border-gray-300 bg-white px-3.5 py-1.5 text-xs font-medium text-gray-700 transition hover:border-brand hover:bg-brand/5 hover:text-brand-dark disabled:opacity-50"
      >
        {label}
      </button>
    );
  }

  /* ---- match detail (lazy "Why") ---- */
  async function loadDetail(id: string): Promise<MatchDetail> {
    const cached = matchDetailCache.current.get(id);
    if (cached) return cached;
    const d = await api.get<MatchDetail>(`/matches/${id}`);
    matchDetailCache.current.set(id, d);
    return d;
  }

  const toggleCompare = (m: Match) =>
    setCompare((prev) =>
      prev.find((x) => x.id === m.id)
        ? prev.filter((x) => x.id !== m.id)
        : prev.length >= 5 ? prev : [...prev, m]
    );
  const toggleSave = (m: Match) =>
    setSaved((prev) => {
      const n = { ...prev };
      if (n[m.id]) delete n[m.id]; else n[m.id] = m;
      return n;
    });

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-2xl font-bold">Sospana Sonke Career Agent</h1>
        <p className="mt-1 text-sm text-gray-500">
          Ask in plain English. I read your profile and the live vacancy index, rank real opportunities,
          and explain every match honestly — no invented jobs, no false promises.
        </p>
      </header>

      {err && <Alert kind="error">{err}</Alert>}

      {/* Quick actions */}
      <div className="flex flex-wrap gap-2">
        {quick("💼 Jobs I can apply for", "Find jobs I can apply for")}
        {quick("📈 Jobs I'm almost qualified for", "Show jobs I'm almost qualified for")}
        {quick("🧭 Discover careers for me", "Discover related careers for me")}
        {quick("💧 Water treatment jobs", "water treatment jobs")}
        {quick("⚙️ Operations management", "operations management jobs")}
      </div>

      {/* Transcript */}
      <Card className="!p-0 overflow-hidden">
        <div ref={scrollRef} className="max-h-[62vh] min-h-[280px] overflow-y-auto px-4 py-5 sm:px-6">
          {turns.length === 0 && (
            <div className="mx-auto max-w-lg py-8 text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-brand to-navy text-xl text-white shadow">✦</div>
              <p className="text-sm text-gray-600">
                Try: <span className="font-medium text-gray-800">&ldquo;water treatment jobs in Gauteng needing a diploma&rdquo;</span>,
                {" "}or tap a quick action above.
              </p>
            </div>
          )}
          <div className="space-y-5">
            {turns.map((t) =>
              t.role === "user" ? (
                <div key={t.id} className="flex justify-end">
                  <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-brand px-4 py-2.5 text-sm text-white shadow-sm">
                    {t.text}
                  </div>
                </div>
              ) : (
                <AgentBubble
                  key={t.id}
                  turn={t}
                  onChip={(role) => submit(role)}
                  loadDetail={loadDetail}
                  compareIds={compare.map((c) => c.id)}
                  savedIds={Object.keys(saved)}
                  onCompare={toggleCompare}
                  onSave={toggleSave}
                />
              )
            )}
            {busy && (
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <Spinner label="Searching the live index…" />
              </div>
            )}
          </div>
        </div>

        {/* Composer */}
        <div className="border-t border-gray-200/80 bg-gray-50/60 p-3">
          <form
            onSubmit={(e) => { e.preventDefault(); submit(input); }}
            className="flex items-center gap-2"
          >
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask the Career Agent…"
              className="flex-1"
              disabled={busy}
              aria-label="Ask the Career Agent"
            />
            <Button type="submit" loading={busy} disabled={!input.trim()}>Send</Button>
          </form>
        </div>
      </Card>

      {/* Trays */}
      {(compare.length > 0 || Object.keys(saved).length > 0) && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-200/80 bg-white px-4 py-3 text-sm shadow-sm">
          {Object.keys(saved).length > 0 && (
            <span className="text-gray-600">⭐ {Object.keys(saved).length} saved</span>
          )}
          {compare.length > 0 && (
            <>
              <span className="text-gray-600">⚖️ {compare.length} to compare</span>
              <Button size="sm" onClick={() => setShowCompare(true)}>Compare now</Button>
              <button onClick={() => setCompare([])} className="text-xs text-gray-400 hover:text-gray-600">clear</button>
            </>
          )}
          <Link href="/matches" className="ml-auto text-xs font-medium text-brand hover:underline">See all matches →</Link>
        </div>
      )}

      {showCompare && <CompareModal items={compare} onClose={() => setShowCompare(false)} loadDetail={loadDetail} />}

      <p className="text-center text-xs text-gray-400">
        Match scores are guidance to help you prioritise — they are not hiring decisions, and every requirement
        is the employer&rsquo;s own. Always confirm details on the original vacancy before applying.
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Agent bubble: text + cards + chips + CTAs                           */
/* ------------------------------------------------------------------ */

function AgentBubble({
  turn, onChip, loadDetail, compareIds, savedIds, onCompare, onSave,
}: {
  turn: AgentTurn;
  onChip: (role: string) => void;
  loadDetail: (id: string) => Promise<MatchDetail>;
  compareIds: string[];
  savedIds: string[];
  onCompare: (m: Match) => void;
  onSave: (m: Match) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="flex gap-2.5">
        <div className="mt-0.5 flex h-7 w-7 flex-none items-center justify-center rounded-lg bg-gradient-to-br from-brand to-navy text-xs text-white shadow">✦</div>
        <div className="max-w-[92%] rounded-2xl rounded-tl-sm bg-gray-100 px-4 py-2.5 text-sm leading-relaxed text-gray-800">
          {turn.text}
        </div>
      </div>

      {turn.roleChips && turn.roleChips.length > 0 && (
        <div className="ml-9 flex flex-wrap gap-2">
          {turn.roleChips.map((r) => (
            <button
              key={r}
              onClick={() => onChip(r)}
              className="rounded-full border border-brand/30 bg-brand/5 px-3 py-1.5 text-xs font-medium text-brand-dark transition hover:bg-brand/10"
            >
              {r} →
            </button>
          ))}
        </div>
      )}

      {turn.matches && turn.matches.length > 0 && (
        <div className="ml-0 grid gap-3 sm:ml-9">
          {turn.matches.map((m) => (
            <MatchCard
              key={m.id}
              m={m}
              loadDetail={loadDetail}
              inCompare={compareIds.includes(m.id)}
              inSaved={savedIds.includes(m.id)}
              onCompare={onCompare}
              onSave={onSave}
            />
          ))}
        </div>
      )}

      {turn.vacancies && turn.vacancies.length > 0 && (
        <div className="ml-0 grid gap-3 sm:ml-9">
          {turn.vacancies.map((v) => <VacancyCard key={v.vacancy.id} data={v} />)}
        </div>
      )}

      {turn.cta && turn.cta.length > 0 && (
        <div className="ml-9 flex flex-wrap gap-2">
          {turn.cta.map((c) =>
            c.href.startsWith("#") ? null : (
              <Link key={c.label} href={c.href}>
                <Button variant="ghost" size="sm">{c.label}</Button>
              </Link>
            )
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Personalized (scored) match card                                    */
/* ------------------------------------------------------------------ */

function MatchCard({
  m, loadDetail, inCompare, inSaved, onCompare, onSave,
}: {
  m: Match;
  loadDetail: (id: string) => Promise<MatchDetail>;
  inCompare: boolean;
  inSaved: boolean;
  onCompare: (m: Match) => void;
  onSave: (m: Match) => void;
}) {
  const [detail, setDetail] = useState<MatchDetail | null>(null);
  const [open, setOpen] = useState(false);
  const [loadingD, setLoadingD] = useState(false);
  const elig = eligibility(m);

  async function toggleWhy() {
    setOpen((v) => !v);
    if (!detail && !loadingD) {
      setLoadingD(true);
      try { setDetail(await loadDetail(m.id)); } catch { /* ignore */ } finally { setLoadingD(false); }
    }
  }

  return (
    <Card className="!p-4" accent={m.band === "Strong" ? "teal" : m.band === "Good" ? "sky" : "gold"}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate font-semibold text-gray-900">{m.vacancy_title || "Vacancy"}</div>
          <div className="truncate text-sm text-gray-500">{m.company_name || "Employer"}</div>
          <div className={`mt-1 text-xs font-medium ${elig.cls}`}>
            {!m.hard_ok && "⚠ "}{elig.label}
          </div>
        </div>
        <div className="flex flex-none flex-col items-end">
          <span className={`text-2xl font-bold leading-none ${scoreColor(m.score)}`}>{Math.round(m.score)}%</span>
          <div className="mt-1"><Badge>{m.band}</Badge></div>
        </div>
      </div>

      {open && (
        <div className="mt-3 border-t border-gray-100 pt-3">
          {loadingD && <div className="text-xs text-gray-400">Loading breakdown…</div>}
          {detail && (
            <div className="space-y-3">
              {detail.reasons.length > 0 && (
                <div>
                  <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-green-700">Why this matches you</div>
                  <ul className="space-y-1 text-sm text-gray-700">
                    {detail.reasons.map((r, i) => <li key={i}>✓ {r}</li>)}
                  </ul>
                </div>
              )}
              {detail.gaps.length > 0 && (
                <div>
                  <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-coral">Gaps to be aware of</div>
                  <ul className="space-y-1 text-sm text-gray-700">
                    {detail.gaps.map((g, i) => <li key={i}>⚠ {g}</li>)}
                  </ul>
                </div>
              )}
              {Object.keys(detail.sub_scores).length > 0 && (
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {Object.entries(detail.sub_scores).map(([k, v]) => (
                    <div key={k} className="rounded-lg bg-gray-50 px-2.5 py-1.5">
                      <div className="text-[11px] capitalize text-gray-500">{k.replace(/_/g, " ")}</div>
                      <div className="text-sm font-semibold text-gray-800">{Math.round(v)}%</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button onClick={toggleWhy} className="text-xs font-medium text-brand hover:underline">
          {open ? "Hide details" : "Why? / breakdown"}
        </button>
        <span className="text-gray-300">·</span>
        <Link href={`/matches/${m.id}`} className="text-xs font-medium text-brand hover:underline">View & apply →</Link>
        <span className="text-gray-300">·</span>
        <Link href={`/matches/${m.id}`} className="text-xs font-medium text-brand hover:underline">Tailor my CV</Link>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => onSave(m)}
            className={`rounded-md px-2 py-1 text-xs font-medium transition ${inSaved ? "bg-gold/20 text-[#8a6d00]" : "text-gray-500 hover:bg-gray-100"}`}
          >
            {inSaved ? "★ Saved" : "☆ Save"}
          </button>
          <button
            onClick={() => onCompare(m)}
            className={`rounded-md px-2 py-1 text-xs font-medium transition ${inCompare ? "bg-brand/10 text-brand-dark" : "text-gray-500 hover:bg-gray-100"}`}
          >
            {inCompare ? "In compare" : "Compare"}
          </button>
        </div>
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Directory (keyword) vacancy card — honest, unscored                 */
/* ------------------------------------------------------------------ */

function VacancyCard({ data }: { data: VacancyCardData }) {
  const { vacancy: v, employer, employerCareers } = data;
  const close = closingStatus(v.closing_date);
  const applyUrl = v.application_url || v.source_url || employerCareers || null;
  return (
    <Card className="!p-4" accent="navy">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate font-semibold text-gray-900">{v.title}</div>
          <div className="truncate text-sm text-gray-500">{employer || "Employer (see source)"}</div>
        </div>
        <span className={`flex-none rounded-full px-2.5 py-1 text-[11px] font-semibold ${close.cls}`}>{close.label}</span>
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
        {v.location && <span>📍 {v.location}</span>}
        {v.employment_type && <span>🗂️ {v.employment_type}</span>}
        {v.work_mode && <span>🏢 {v.work_mode}</span>}
        <span>💰 {v.salary || "Not disclosed"}</span>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        {applyUrl ? (
          <a href={applyUrl} target="_blank" rel="noopener noreferrer">
            <Button variant="ghost" size="sm">View / apply on source →</Button>
          </a>
        ) : (
          <span className="text-xs text-gray-400">No application link provided</span>
        )}
        <span className="ml-auto text-[11px] text-gray-400">Source: Sospana Sonke directory</span>
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Compare modal (blueprint section 20)                                */
/* ------------------------------------------------------------------ */

function CompareModal({
  items, onClose, loadDetail,
}: {
  items: Match[];
  onClose: () => void;
  loadDetail: (id: string) => Promise<MatchDetail>;
}) {
  const [details, setDetails] = useState<Record<string, MatchDetail>>({});
  useEffect(() => {
    let live = true;
    Promise.all(items.map((m) => loadDetail(m.id).then((d) => [m.id, d] as const).catch(() => null)))
      .then((pairs) => {
        if (!live) return;
        const map: Record<string, MatchDetail> = {};
        pairs.forEach((p) => { if (p) map[p[0]] = p[1]; });
        setDetails(map);
      });
    return () => { live = false; };
  }, [items, loadDetail]);

  const subKeys = Array.from(
    new Set(Object.values(details).flatMap((d) => Object.keys(d.sub_scores)))
  );

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4" onClick={onClose}>
      <div
        className="max-h-[85vh] w-full max-w-3xl overflow-auto rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold">Compare vacancies</h2>
          <button onClick={onClose} className="rounded-md px-2 py-1 text-sm text-gray-500 hover:bg-gray-100">Close ✕</button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="p-2 text-left font-medium text-gray-400"></th>
                {items.map((m) => (
                  <th key={m.id} className="min-w-[9rem] p-2 text-left align-top">
                    <div className="font-semibold text-gray-900">{m.vacancy_title}</div>
                    <div className="text-xs font-normal text-gray-500">{m.company_name}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <Row label="Match score" cells={items.map((m) => `${Math.round(m.score)}%`)} />
              <Row label="Band" cells={items.map((m) => m.band)} />
              <Row label="Decision" cells={items.map((m) => m.decision.replace(/_/g, " "))} />
              <Row label="Hard requirements" cells={items.map((m) => (m.hard_ok ? "Met" : "Not confirmed"))} />
              {subKeys.map((k) => (
                <Row
                  key={k}
                  label={k.replace(/_/g, " ")}
                  cells={items.map((m) => {
                    const v = details[m.id]?.sub_scores?.[k];
                    return v == null ? "—" : `${Math.round(v)}%`;
                  })}
                />
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {items.map((m) => (
            <Link key={m.id} href={`/matches/${m.id}`}>
              <Button size="sm" variant="ghost">Open {m.vacancy_title?.slice(0, 20)} →</Button>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

function Row({ label, cells }: { label: string; cells: string[] }) {
  return (
    <tr className="border-t border-gray-100">
      <td className="p-2 align-top text-xs font-medium capitalize text-gray-500">{label}</td>
      {cells.map((c, i) => <td key={i} className="p-2 align-top text-gray-800">{c}</td>)}
    </tr>
  );
}

/* ------------------------------------------------------------------ */
/* helpers + types                                                     */
/* ------------------------------------------------------------------ */

interface ProfileLite {
  current_occupation?: string | null;
  desired_occupations?: string[] | null;
  industries?: string[] | null;
  preferred_locations?: string[] | null;
  years_experience?: number | null;
}

function titleCase(s: string): string {
  return s.replace(/\w\S*/g, (w) => w.charAt(0).toUpperCase() + w.slice(1));
}

function describeFilters(f: ParsedFilters): string {
  const parts: string[] = [];
  if (f.location) parts.push(`in ${titleCase(f.location)}`);
  if (f.qualification) parts.push(`(${f.qualification})`);
  if (f.minYears) parts.push(`${f.minYears}+ yrs`);
  if (f.workMode) parts.push(f.workMode);
  if (f.employmentType) parts.push(f.employmentType);
  if (f.minSalary) parts.push(`min R${f.minSalary.toLocaleString()}`);
  return parts.length ? ` ${parts.join(", ")}` : "";
}

export default function AgentPage() {
  return (
    <Guard>
      <AgentInner />
    </Guard>
  );
}
