"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Alert, Button, Card, Field, Input, Select, Spinner, StatusBadge, Textarea } from "@/components/ui";
import type { UploadedCv } from "@/lib/types";

/* ---------- Types (mirror backend/app/schemas/cv_audit.py) ---------- */

type Area = { label: string; score: number; basis: string[] };
type Scores = { overall: number; areas: Record<string, Area>; disclaimer: string };
type Experience = {
  position: string | null; employer: string | null; location: string | null;
  start: string | null; end: string | null; is_current: boolean; bullets: string[]; needs_review: boolean;
};
type Education = {
  qualification: string | null; institution: string | null; date_text: string | null; year: number | null;
  status: "completed" | "in_progress" | "awaiting_conferral" | "unverified"; nqf: string | null;
};
type Cert = { name: string; issuer: string | null; year: string | null; kind: string; status: string };
type Rebuilt = {
  full_name: string | null; headline: string | null; email: string | null; phone: string | null;
  location: string | null; linkedin_url: string | null; links: string[]; summary: string | null;
  competencies: Record<string, string[]>; software: string[]; experience: Experience[];
  education: Education[]; current_studies: Education[]; certifications: Cert[]; short_courses: Cert[];
  in_progress_certs: Cert[]; registrations: Cert[]; projects: string[]; achievements: string[];
  languages: string[]; drivers_licence: string | null;
};
type Check = { area: string; ok: boolean; detail: string };
type ChecklistItem = { category: string; item: string; why: string; priority: "high" | "medium" | "low" };
type Direction = { id: string; title: string; why: string; emphasise: string[]; credentials: string[]; targeted_cv: string };
type Finding = { code: string; severity: "high" | "medium" | "low"; area: string; message: string; impact: string };
type AuditSummary = {
  id: string; cv_id: string; source_filename: string; original_scores: Scores; final_scores: Scores;
  edited_by_candidate: boolean; created_at: string;
};
type Audit = AuditSummary & {
  document_facts: Record<string, unknown>; findings: Finding[];
  weaknesses: { issue: string; impact: string; severity: string }[];
  rebuilt: Rebuilt; change_log: { area: string; change: string }[];
  stress: { checks: Check[]; passed: number; total: number; pages: number; compact: boolean; extracted_text_preview: string };
  pages: number; limitations: string[]; checklist: ChecklistItem[]; directions: Direction[];
};

const TABS = ["Overview", "Rebuilt CV", "Stress test", "Checklist", "Career directions"] as const;
type Tab = (typeof TABS)[number];

const STATUS_OPTIONS: { value: Education["status"]; label: string }[] = [
  { value: "completed", label: "Completed" },
  { value: "in_progress", label: "In progress" },
  { value: "awaiting_conferral", label: "Completed – awaiting conferral" },
  { value: "unverified", label: "Status to be confirmed" },
];

const LOADING_LINES = [
  "Reading your CV the way a recruitment robot would…",
  "Checking for tables that ATS software loves to scramble…",
  "Removing “hardworking team player” with surgical precision…",
  "Making sure we don't invent a single number. Promise.",
];

/* ---------- Small pieces ---------- */

function ScoreBar({ before, after, label }: { before: number; after: number; label: string }) {
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between text-sm">
        <span className="font-medium text-ss-text">{label}</span>
        <span className="tabular-nums text-ss-muted">
          {before} → <span className="font-semibold text-ss-text">{after}</span>
        </span>
      </div>
      <div className="relative h-2.5 overflow-hidden rounded-full bg-ss-border" aria-hidden>
        <div className="absolute inset-y-0 left-0 rounded-full bg-ss-tech transition-all duration-700" style={{ width: `${after}%` }} />
        <div className="absolute inset-y-0 w-1 rounded-full bg-ss-primary" style={{ left: `calc(${before}% - 2px)` }} title="Original score" />
      </div>
    </div>
  );
}

function Ring({ value, label }: { value: number; label: string }) {
  const r = 34, c = 2 * Math.PI * r;
  return (
    <div className="flex flex-col items-center">
      <svg width="88" height="88" viewBox="0 0 88 88" role="img" aria-label={`${label}: ${value} out of 100`}>
        <circle cx="44" cy="44" r={r} fill="none" stroke="currentColor" className="text-ss-border" strokeWidth="8" />
        <circle cx="44" cy="44" r={r} fill="none" stroke="currentColor" className="text-ss-tech" strokeWidth="8"
          strokeDasharray={c} strokeDashoffset={c * (1 - value / 100)} strokeLinecap="round" transform="rotate(-90 44 44)" />
        <text x="44" y="50" textAnchor="middle" className="fill-current text-ss-text" fontSize="20" fontWeight="700">{value}</text>
      </svg>
      <span className="mt-1 text-xs font-medium uppercase tracking-wide text-ss-muted">{label}</span>
    </div>
  );
}

const sevTone = (s: string) => (s === "high" ? "closing" : s === "medium" ? "new" : "neutral") as "closing" | "new" | "neutral";

/* ---------- Page ---------- */

function CvAuditInner() {
  const [cvs, setCvs] = useState<UploadedCv[] | null>(null);
  const [audits, setAudits] = useState<AuditSummary[]>([]);
  const [selectedCv, setSelectedCv] = useState("");
  const [audit, setAudit] = useState<Audit | null>(null);
  const [draft, setDraft] = useState<Rebuilt | null>(null);
  const [tab, setTab] = useState<Tab>("Overview");
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [line, setLine] = useState(0);

  useEffect(() => {
    api.get<UploadedCv[]>("/cv").then((rows) => {
      setCvs(rows);
      const fromUrl = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("cv") : null;
      const usable = rows.filter((r) => r.parse_status !== "failed");
      setSelectedCv(fromUrl && rows.some((r) => r.id === fromUrl) ? fromUrl : usable[0]?.id || "");
    }).catch((e) => setErr(e.message));
    api.get<AuditSummary[]>("/cv-audits").then(setAudits).catch(() => setAudits([]));
  }, []);

  useEffect(() => {
    if (!busy) return;
    const t = setInterval(() => setLine((n) => (n + 1) % LOADING_LINES.length), 2200);
    return () => clearInterval(t);
  }, [busy]);

  function open(a: Audit) {
    setAudit(a);
    setDraft(JSON.parse(JSON.stringify(a.rebuilt)));
    setTab("Overview");
  }

  async function upload(file: File) {
    setErr(""); setBusy(true);
    try {
      const cv = await api.upload<UploadedCv>("/cv", file);
      setCvs((prev) => [cv, ...(prev || [])]);
      setSelectedCv(cv.id);
      if (cv.parse_status === "failed") setErr(cv.parse_error || "We couldn't read text from that file.");
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function run() {
    if (!selectedCv) return;
    setErr(""); setMsg(""); setBusy(true);
    try {
      const a = await api.post<Audit>("/cv-audits", { cv_id: selectedCv });
      open(a);
      setAudits((prev) => [a, ...prev]);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function load(id: string) {
    setErr(""); setBusy(true);
    try { open(await api.get<Audit>(`/cv-audits/${id}`)); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  async function removeAudit(id: string) {
    if (!window.confirm("Delete this audit and its rebuilt CV? Your uploaded original is not affected.")) return;
    await api.del(`/cv-audits/${id}`);
    setAudits((prev) => prev.filter((a) => a.id !== id));
    if (audit?.id === id) { setAudit(null); setDraft(null); }
  }

  async function save() {
    if (!audit || !draft) return;
    setSaving(true); setErr(""); setMsg("");
    try {
      const a = await api.put<Audit>(`/cv-audits/${audit.id}/cv`, draft);
      open(a);
      setTab("Rebuilt CV");
      setMsg(`Saved. The stress test re-ran: ${a.stress.passed}/${a.stress.total} checks passed, overall score ${a.final_scores.overall}.`);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  function dl(kind: "docx" | "pdf" | "report") {
    if (!audit) return;
    const base = (audit.rebuilt.full_name || "CV").replace(/[^A-Za-z0-9_-]+/g, "_");
    const name = kind === "report" ? `${base}_ATS_Audit_Report.pdf` : `${base}_CV.${kind}`;
    api.download(`/cv-audits/${audit.id}/file/${kind}`, name).catch((e) => setErr(e.message));
  }

  const dirty = useMemo(() => audit && draft && JSON.stringify(draft) !== JSON.stringify(audit.rebuilt), [audit, draft]);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ss-tech">CV Doctor</p>
        <h1 className="text-2xl font-bold text-ss-text sm:text-3xl">ATS CV Audit &amp; Rebuild</h1>
        <p className="mt-1 max-w-3xl text-ss-muted">
          We audit your uploaded CV the way screening software and recruiters read it, rebuild it into a polished,
          single-column, ATS-safe CV (Word and PDF), stress-test the finished files, and give you a checklist of anything
          only you can confirm. Nothing is invented — no figures, titles or qualifications are added that your CV doesn&apos;t state.
        </p>
      </div>

      {err && <Alert kind="error">{err}</Alert>}
      {msg && <Alert kind="success">{msg}</Alert>}

      <Card>
        <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
          <Field label="Choose a CV to audit" hint="PDF (text-based), Word (.docx) or .txt — the original is never changed.">
            {cvs === null ? <Spinner /> : cvs.length === 0 ? (
              <p className="text-sm text-ss-muted">No CV uploaded yet — add one below.</p>
            ) : (
              <Select value={selectedCv} onChange={(e) => setSelectedCv(e.target.value)}>
                {cvs.map((c) => (
                  <option key={c.id} value={c.id} disabled={c.parse_status === "failed"}>
                    {c.original_filename}{c.parse_status === "failed" ? " (unreadable)" : ""} · {new Date(c.created_at).toLocaleDateString()}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <div className="flex flex-wrap gap-2">
            <label className="inline-flex cursor-pointer items-center rounded-xl border border-ss-border px-4 py-2 text-sm font-medium text-ss-text hover:border-ss-tech">
              Upload new CV
              <input type="file" accept=".pdf,.docx,.txt" className="sr-only"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ""; }} />
            </label>
            <Button onClick={run} disabled={!selectedCv || busy} loading={busy}>Audit &amp; rebuild</Button>
          </div>
        </div>
        {busy && <p className="mt-3 text-sm text-ss-muted" aria-live="polite">{LOADING_LINES[line]}</p>}
      </Card>

      {audits.length > 0 && !audit && (
        <Card>
          <h2 className="mb-3 font-semibold text-ss-text">Previous audits</h2>
          <ul className="divide-y divide-ss-border">
            {audits.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                <span className="min-w-0 break-words text-ss-text">
                  {a.source_filename} · {new Date(a.created_at).toLocaleDateString()} ·{" "}
                  <span className="text-ss-muted">{a.original_scores.overall} → {a.final_scores.overall}</span>
                  {a.edited_by_candidate && <span className="ml-2 text-xs text-ss-tech">edited</span>}
                </span>
                <span className="flex gap-3">
                  <button className="font-medium text-ss-tech hover:underline" onClick={() => load(a.id)}>Open</button>
                  <button className="font-medium text-ss-danger hover:underline" onClick={() => removeAudit(a.id)}>Delete</button>
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {audit && draft && (
        <>
          <Card>
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex gap-6">
                <Ring value={audit.original_scores.overall} label="Original" />
                <Ring value={audit.final_scores.overall} label="Rebuilt" />
              </div>
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => dl("docx")}>Download Word (.docx)</Button>
                <Button variant="secondary" onClick={() => dl("pdf")}>Download PDF</Button>
                <Button variant="ghost" onClick={() => dl("report")}>Audit report (PDF)</Button>
              </div>
            </div>
            <p className="mt-3 text-xs text-ss-muted">{audit.final_scores.disclaimer}</p>
            <div className="mt-2 flex flex-wrap gap-2 text-xs">
              <StatusBadge tone={audit.stress.passed === audit.stress.total ? "verified" : "closing"}>
                {`Stress test ${audit.stress.passed}/${audit.stress.total}`}
              </StatusBadge>
              <StatusBadge tone="neutral">{`${audit.pages} page${audit.pages === 1 ? "" : "s"}`}</StatusBadge>
              {audit.checklist.some((c) => c.priority === "high") && (
                <StatusBadge tone="new">{`${audit.checklist.filter((c) => c.priority === "high").length} items to confirm`}</StatusBadge>
              )}
            </div>
          </Card>

          <div role="tablist" className="flex flex-wrap gap-2">
            {TABS.map((t) => (
              <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
                className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${tab === t ? "bg-ss-tech text-white" : "border border-ss-border text-ss-text hover:border-ss-tech"}`}>
                {t}
              </button>
            ))}
            <button className="ml-auto text-sm text-ss-muted hover:underline" onClick={() => { setAudit(null); setDraft(null); }}>
              ← All audits
            </button>
          </div>

          {tab === "Overview" && (
            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <h2 className="mb-4 font-semibold text-ss-text">Scores: original → rebuilt</h2>
                <div className="space-y-4">
                  {Object.entries(audit.final_scores.areas).map(([k, a]) => (
                    <details key={k} className="group">
                      <summary className="cursor-pointer list-none">
                        <ScoreBar label={a.label} before={audit.original_scores.areas[k].score} after={a.score} />
                      </summary>
                      <ul className="mt-2 space-y-1 pl-1 text-xs text-ss-muted">
                        {a.basis.map((b, i) => <li key={i}>{b}</li>)}
                      </ul>
                    </details>
                  ))}
                </div>
                <p className="mt-3 text-xs text-ss-muted">Tap a score to see exactly how it was worked out.</p>
              </Card>
              <Card>
                <h2 className="mb-3 font-semibold text-ss-text">What was holding the original back</h2>
                <ul className="space-y-3 text-sm">
                  {audit.weaknesses.map((w, i) => (
                    <li key={i}>
                      <StatusBadge tone={sevTone(w.severity)}>{w.severity}</StatusBadge>
                      <div className="mt-1 text-ss-text">{w.issue}</div>
                      <div className="text-xs text-ss-muted">{w.impact}</div>
                    </li>
                  ))}
                  {audit.weaknesses.length === 0 && <li className="text-ss-muted">No significant weaknesses found.</li>}
                </ul>
              </Card>
              <Card className="lg:col-span-2">
                <h2 className="mb-3 font-semibold text-ss-text">What we changed</h2>
                <ul className="list-disc space-y-1 pl-5 text-sm text-ss-text">
                  {audit.change_log.map((c, i) => <li key={i}><span className="font-medium">{c.area}:</span> {c.change}</li>)}
                </ul>
                {audit.limitations.length > 0 && (
                  <>
                    <h3 className="mb-2 mt-5 font-semibold text-ss-text">Remaining limitations</h3>
                    <ul className="list-disc space-y-1 pl-5 text-sm text-ss-muted">
                      {audit.limitations.map((l, i) => <li key={i}>{l}</li>)}
                    </ul>
                  </>
                )}
              </Card>
            </div>
          )}

          {tab === "Rebuilt CV" && (
            <RebuiltEditor draft={draft} setDraft={setDraft} dirty={!!dirty} saving={saving} onSave={save}
              onReset={() => setDraft(JSON.parse(JSON.stringify(audit.rebuilt)))} />
          )}

          {tab === "Stress test" && (
            <Card>
              <h2 className="mb-1 font-semibold text-ss-text">ATS stress test on the finished files</h2>
              <p className="mb-4 text-sm text-ss-muted">
                Both files were generated, re-opened, their text extracted and re-parsed — exactly what an ATS does.
              </p>
              <ul className="space-y-3">
                {audit.stress.checks.map((c, i) => (
                  <li key={i} className="flex gap-3 text-sm">
                    <span aria-hidden className={`mt-0.5 font-bold ${c.ok ? "text-ss-success" : "text-ss-danger"}`}>{c.ok ? "✓" : "!"}</span>
                    <span><span className="font-medium text-ss-text">{c.area}</span>{" "}
                      <span className="sr-only">{c.ok ? "passed" : "needs attention"}</span>
                      <span className="text-ss-muted">— {c.detail}</span></span>
                  </li>
                ))}
              </ul>
              <details className="mt-5">
                <summary className="cursor-pointer text-sm font-medium text-ss-tech">See the plain text an ATS extracts from your PDF</summary>
                <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap rounded-xl bg-ss-bg p-3 text-xs text-ss-text">{audit.stress.extracted_text_preview}</pre>
              </details>
            </Card>
          )}

          {tab === "Checklist" && (
            <Card>
              <h2 className="mb-1 font-semibold text-ss-text">Outstanding information</h2>
              <p className="mb-4 text-sm text-ss-muted">
                Nothing here was guessed for you. Fill these in on the <button className="text-ss-tech underline" onClick={() => setTab("Rebuilt CV")}>Rebuilt CV</button> tab, save, and download again.
              </p>
              {Array.from(new Set(audit.checklist.map((c) => c.category))).map((cat) => (
                <div key={cat} className="mb-5">
                  <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-ss-muted">{cat}</h3>
                  <ul className="space-y-2">
                    {audit.checklist.filter((c) => c.category === cat).map((c, i) => (
                      <li key={i} className="rounded-xl border border-ss-border p-3 text-sm">
                        <div className="flex items-start gap-2">
                          {c.priority === "high" && <StatusBadge tone="closing">confirm</StatusBadge>}
                          {c.priority === "low" && <StatusBadge tone="neutral">optional</StatusBadge>}
                          <span className="text-ss-text">{c.item}</span>
                        </div>
                        <p className="mt-1 text-xs text-ss-muted">{c.why}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </Card>
          )}

          {tab === "Career directions" && (
            <div className="grid gap-4 md:grid-cols-3">
              {audit.directions.length === 0 && <Card><p className="text-sm text-ss-muted">Not enough evidence in this CV to suggest directions yet.</p></Card>}
              {audit.directions.map((d) => (
                <Card key={d.id}>
                  <h2 className="font-semibold text-ss-text">{d.title}</h2>
                  <p className="mt-1 text-sm text-ss-muted">{d.why}</p>
                  <h3 className="mt-3 text-xs font-semibold uppercase tracking-wide text-ss-muted">Emphasise</h3>
                  <ul className="list-disc pl-5 text-sm text-ss-text">{d.emphasise.map((x) => <li key={x}>{x}</li>)}</ul>
                  <h3 className="mt-3 text-xs font-semibold uppercase tracking-wide text-ss-muted">Could strengthen</h3>
                  <ul className="list-disc pl-5 text-sm text-ss-text">{d.credentials.map((x) => <li key={x}>{x}</li>)}</ul>
                  <p className="mt-3 text-xs text-ss-muted"><span className="font-semibold">Targeted CV:</span> {d.targeted_cv}</p>
                </Card>
              ))}
              <p className="text-xs text-ss-muted md:col-span-3">
                Suggestions only — check each vacancy&apos;s real requirements. For a specific job, use{" "}
                <Link href="/tailor" className="text-ss-tech underline">Tailor my CV to a job</Link>.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ---------- Editor ---------- */

function lines(v: string) { return v.split("\n").map((s) => s.trim()).filter(Boolean); }

function RebuiltEditor({ draft, setDraft, dirty, saving, onSave, onReset }: {
  draft: Rebuilt; setDraft: (r: Rebuilt) => void; dirty: boolean; saving: boolean; onSave: () => void; onReset: () => void;
}) {
  const set = <K extends keyof Rebuilt>(k: K, v: Rebuilt[K]) => setDraft({ ...draft, [k]: v });
  const setExp = (i: number, patch: Partial<Experience>) =>
    set("experience", draft.experience.map((e, j) => (j === i ? { ...e, ...patch } : e)));
  const setEdu = (key: "education" | "current_studies", i: number, patch: Partial<Education>) =>
    set(key, draft[key].map((e, j) => (j === i ? { ...e, ...patch } : e)));

  return (
    <div className="space-y-4">
      <Alert kind="info">
        You are the author: anything you type here is used as written. Only add figures, titles and dates you can
        stand behind in an interview. Saving re-runs the stress test and scores.
      </Alert>

      <Card>
        <h2 className="mb-3 font-semibold text-ss-text">Header</h2>
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Full name"><Input value={draft.full_name || ""} maxLength={120} onChange={(e) => set("full_name", e.target.value)} /></Field>
          <Field label="Headline"><Input value={draft.headline || ""} maxLength={200} onChange={(e) => set("headline", e.target.value)} /></Field>
          <Field label="Email"><Input value={draft.email || ""} maxLength={200} onChange={(e) => set("email", e.target.value)} /></Field>
          <Field label="Phone"><Input value={draft.phone || ""} maxLength={40} onChange={(e) => set("phone", e.target.value)} /></Field>
          <Field label="City, province"><Input value={draft.location || ""} maxLength={120} onChange={(e) => set("location", e.target.value)} /></Field>
          <Field label="LinkedIn URL (optional)"><Input value={draft.linkedin_url || ""} maxLength={300} onChange={(e) => set("linkedin_url", e.target.value || null)} /></Field>
        </div>
        <div className="mt-3">
          <Field label="Professional summary">
            <Textarea rows={5} maxLength={2500} value={draft.summary || ""} onChange={(e) => set("summary", e.target.value)} />
          </Field>
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 font-semibold text-ss-text">Core competencies</h2>
        <div className="space-y-3">
          {Object.entries(draft.competencies).map(([g, ts]) => (
            <Field key={g} label={g} hint="Comma-separated">
              <Input value={ts.join(", ")} onChange={(e) => set("competencies", { ...draft.competencies, [g]: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })} />
            </Field>
          ))}
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 font-semibold text-ss-text">Professional experience</h2>
        <div className="space-y-6">
          {draft.experience.map((e, i) => (
            <div key={i} className="rounded-xl border border-ss-border p-4">
              {e.needs_review && <p className="mb-2 text-xs font-medium text-ss-danger">Please confirm which is the job title and which the employer.</p>}
              <div className="grid gap-3 md:grid-cols-2">
                <Field label="Job title"><Input value={e.position || ""} maxLength={300} onChange={(ev) => setExp(i, { position: ev.target.value, needs_review: false })} /></Field>
                <Field label="Employer"><Input value={e.employer || ""} maxLength={300} onChange={(ev) => setExp(i, { employer: ev.target.value, needs_review: false })} /></Field>
                <Field label="Location"><Input value={e.location || ""} maxLength={300} onChange={(ev) => setExp(i, { location: ev.target.value || null })} /></Field>
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Start (e.g. Mar 2022)"><Input value={e.start || ""} maxLength={40} onChange={(ev) => setExp(i, { start: ev.target.value || null })} /></Field>
                  <Field label="End"><Input value={e.is_current ? "Present" : e.end || ""} disabled={e.is_current} maxLength={40} onChange={(ev) => setExp(i, { end: ev.target.value || null })} /></Field>
                </div>
              </div>
              <label className="mt-2 flex items-center gap-2 text-sm text-ss-text">
                <input type="checkbox" checked={e.is_current} onChange={(ev) => setExp(i, { is_current: ev.target.checked, end: ev.target.checked ? "Present" : e.end === "Present" ? null : e.end })} />
                I currently work here (bullets in present tense)
              </label>
              <div className="mt-3">
                <Field label="Bullet points" hint="One per line. Add a real figure where you can evidence it.">
                  <Textarea rows={Math.max(4, e.bullets.length + 1)} value={e.bullets.join("\n")} onChange={(ev) => setExp(i, { bullets: ev.target.value.split("\n") })}
                    onBlur={(ev) => setExp(i, { bullets: lines(ev.target.value) })} />
                </Field>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {(["education", "current_studies"] as const).map((key) => draft[key].length > 0 && (
        <Card key={key}>
          <h2 className="mb-3 font-semibold text-ss-text">{key === "education" ? "Education" : "Current studies"}</h2>
          <div className="space-y-4">
            {draft[key].map((ed, i) => (
              <div key={i} className="grid gap-3 md:grid-cols-4">
                <Field label="Qualification"><Input value={ed.qualification || ""} maxLength={300} onChange={(ev) => setEdu(key, i, { qualification: ev.target.value })} /></Field>
                <Field label="Institution"><Input value={ed.institution || ""} maxLength={300} onChange={(ev) => setEdu(key, i, { institution: ev.target.value })} /></Field>
                <Field label="Date / year"><Input value={ed.date_text || ""} maxLength={60} onChange={(ev) => setEdu(key, i, { date_text: ev.target.value || null })} /></Field>
                <Field label="Status">
                  <Select value={ed.status} onChange={(ev) => setEdu(key, i, { status: ev.target.value as Education["status"] })}>
                    {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </Select>
                </Field>
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs text-ss-muted">Never mark a qualification completed until it has been conferred.</p>
        </Card>
      ))}

      <Card>
        <h2 className="mb-3 font-semibold text-ss-text">Additional information</h2>
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Languages" hint="Comma-separated, e.g. English (fluent), isiZulu (native)">
            <Input value={draft.languages.join(", ")} onChange={(e) => set("languages", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))} />
          </Field>
          <Field label="Driver’s licence"><Input value={draft.drivers_licence || ""} maxLength={60} onChange={(e) => set("drivers_licence", e.target.value || null)} /></Field>
          <Field label="Achievements" hint="One per line — only verified ones">
            <Textarea rows={3} value={draft.achievements.join("\n")} onChange={(e) => set("achievements", e.target.value.split("\n"))} onBlur={(e) => set("achievements", lines(e.target.value))} />
          </Field>
          <Field label="Selected projects" hint="One per line">
            <Textarea rows={3} value={draft.projects.join("\n")} onChange={(e) => set("projects", e.target.value.split("\n"))} onBlur={(e) => set("projects", lines(e.target.value))} />
          </Field>
        </div>
      </Card>

      <div className="sticky bottom-20 z-10 flex flex-wrap items-center justify-end gap-2 rounded-2xl border border-ss-border bg-ss-surface p-3 shadow-lg md:bottom-4">
        {dirty && <span className="mr-auto text-sm text-ss-muted">Unsaved changes</span>}
        <Button variant="ghost" onClick={onReset} disabled={!dirty || saving}>Undo changes</Button>
        <Button onClick={onSave} disabled={!dirty} loading={saving}>Save &amp; re-test</Button>
      </div>
    </div>
  );
}

export default function CvAuditPage() {
  return (
    <Guard>
      <CvAuditInner />
    </Guard>
  );
}
