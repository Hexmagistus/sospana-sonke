"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Field, Input, Textarea, Button, Alert, Spinner, Badge } from "@/components/ui";
import { Banner } from "@/components/Banner";
import type {
  AnalyzeJobResult, JobAnalysisDetail, CvData, TemplateInfo, CVVersion,
} from "@/lib/types";

interface CoverLetterDoc { id: string; label: string; body: string }
interface InterviewPrepDoc {
  id: string;
  content: { questions: string[]; talking_points: string[]; watch_outs: string[]; tips: string[] };
}

const STEPS = ["Target job", "Match report", "Improve & design", "Preview & export"] as const;
type Step = 0 | 1 | 2 | 3;

const SUB_SCORE_LABELS: Record<string, string> = {
  qualification: "Qualifications",
  experience: "Experience",
  technical_skill: "Technical skills",
  industry: "Industry fit",
  certification: "Certifications",
  keyword: "Keyword alignment",
  responsibility: "Responsibilities",
};

function scoreColor(v: number) {
  if (v >= 75) return "text-green-700";
  if (v >= 55) return "text-yellow-700";
  return "text-coral";
}

function ScoreDial({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex flex-col items-center">
      <div className={`text-4xl font-extrabold ${scoreColor(value)}`}>{Math.round(value)}%</div>
      <div className="mt-1 text-xs font-medium text-gray-500">{label}</div>
    </div>
  );
}

function StepBar({ step }: { step: Step }) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs sm:text-sm">
      {STEPS.map((label, i) => (
        <div key={label} className="flex items-center gap-2">
          <span
            className={`flex h-6 w-6 flex-none items-center justify-center rounded-full text-xs font-bold ${
              i < step ? "bg-brand text-white" : i === step ? "bg-gold text-navy" : "bg-gray-200 text-gray-500"
            }`}
          >
            {i < step ? "✓" : i + 1}
          </span>
          <span className={i === step ? "font-semibold text-navy" : "text-gray-500"}>{label}</span>
          {i < STEPS.length - 1 && <span className="mx-1 text-gray-300">—</span>}
        </div>
      ))}
    </div>
  );
}

function RequirementList({
  title, items, tone,
}: {
  title: string;
  items: { text: string; note: string }[];
  tone: "green" | "yellow" | "red";
}) {
  const toneCls = {
    green: "text-green-700",
    yellow: "text-yellow-700",
    red: "text-coral",
  }[tone];
  return (
    <div>
      <h3 className={`mb-2 text-sm font-semibold ${toneCls}`}>{title} ({items.length})</h3>
      {items.length === 0 ? (
        <p className="text-sm text-gray-400">None.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((it, i) => (
            <li key={i} className="rounded-lg bg-gray-50 px-3 py-2 text-sm">
              <div className="font-medium text-gray-800">{it.text}</div>
              <div className="mt-0.5 text-xs text-gray-500">{it.note}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function TailorInner() {
  const [step, setStep] = useState<Step>(0);

  // Step 0: target job form
  const [company, setCompany] = useState("");
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");

  // Step 1/2 state
  const [analysis, setAnalysis] = useState<JobAnalysisDetail | null>(null);
  const [draftCv, setDraftCv] = useState<CvData | null>(null);
  const [violations, setViolations] = useState<string[]>([]);
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [template, setTemplate] = useState("professional");
  const [skillsText, setSkillsText] = useState("");

  // Step 3 state
  const [cvVersion, setCvVersion] = useState<CVVersion | null>(null);
  const [coverLetter, setCoverLetter] = useState<CoverLetterDoc | null>(null);
  const [prep, setPrep] = useState<InterviewPrepDoc | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const c = params.get("company");
    if (c) setCompany(c);
    const t = params.get("title");
    if (t) setTitle(t);
    api.get<TemplateInfo[]>("/tailor/templates").then(setTemplates).catch(() => {});
  }, []);

  async function analyze() {
    if (!desc.trim()) {
      setErr("Paste the job advertisement text so it can be analysed.");
      return;
    }
    setBusy("analyze"); setErr("");
    try {
      const r = await api.post<AnalyzeJobResult>("/tailor/analyze", {
        job_title: title || null,
        company_name: company || null,
        job_description: desc,
      });
      setAnalysis(r.job_analysis);
      setDraftCv(r.draft_cv);
      setViolations(r.fact_check.violations);
      setTemplate(r.job_analysis.template || "professional");
      setSkillsText(r.draft_cv.skills.join(", "));
      setStep(1);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not analyse this job advert. Please try again.");
    } finally {
      setBusy("");
    }
  }

  function updateSummary(v: string) {
    setDraftCv((d) => (d ? { ...d, summary: v } : d));
  }

  function commitSkills() {
    const skills = skillsText.split(",").map((s) => s.trim()).filter(Boolean);
    setDraftCv((d) => (d ? { ...d, skills } : d));
  }

  async function generateCv() {
    if (!analysis || !draftCv) return;
    setBusy("cv"); setErr("");
    try {
      commitSkills();
      const finalCv = { ...draftCv, skills: skillsText.split(",").map((s) => s.trim()).filter(Boolean) };
      const v = await api.post<CVVersion>(`/tailor/${analysis.id}/generate-cv`, { cv_data: finalCv, template });
      setCvVersion(v);
      setStep(3);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not generate the CV. Please try again.");
    } finally {
      setBusy("");
    }
  }

  async function generateCoverLetter() {
    if (!analysis) return;
    setBusy("letter"); setErr("");
    try {
      setCoverLetter(await api.post<CoverLetterDoc>(`/tailor/${analysis.id}/generate-cover-letter`));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not generate the cover letter.");
    } finally {
      setBusy("");
    }
  }

  async function generatePrep() {
    if (!analysis) return;
    setBusy("prep"); setErr("");
    try {
      setPrep(await api.post<InterviewPrepDoc>(`/tailor/${analysis.id}/interview-prep`));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not generate interview preparation.");
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="space-y-6">
      <Banner
        variant="tailor"
        eyebrow="Apply smarter"
        title="Build my job-aligned CV"
        subtitle="Paste a job advert and we'll analyse it against your Master CV, score the match, flag real gaps, and help you rewrite a truthful, tailored CV for it — never fabricated, only rewritten around the job."
      >
        <div className="flex flex-wrap gap-3 text-sm">
          <Link href="/master-cv" className="font-semibold text-gold underline underline-offset-2">
            View my Master CV
          </Link>
          <Link href="/tailor/applications" className="font-semibold text-gold underline underline-offset-2">
            My job applications
          </Link>
        </div>
      </Banner>

      <Card>
        <StepBar step={step} />
      </Card>

      {err && <Alert kind="error">{err}</Alert>}

      {step === 0 && (
        <Card>
          <h2 className="mb-4 text-lg font-semibold">1. Tell us about the job</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Company (optional)">
              <Input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="e.g. Eskom" />
            </Field>
            <Field label="Job title (optional — we'll detect it if left blank)">
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Operations Manager" />
            </Field>
          </div>
          <div className="mt-4">
            <Field label="Paste the full job advertisement" hint="required">
              <Textarea
                value={desc}
                onChange={(e) => setDesc(e.target.value)}
                rows={12}
                placeholder="Paste the entire job description here — requirements, responsibilities, and everything else. We'll extract what matters automatically."
              />
            </Field>
          </div>
          <div className="mt-4">
            <Button onClick={analyze} loading={busy === "analyze"}>
              {busy === "analyze" ? "Analysing…" : "Analyse this job"}
            </Button>
          </div>
        </Card>
      )}

      {step >= 1 && analysis && (
        <>
          <Card accent="teal">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold">
                  {analysis.job_title}{analysis.company_name ? ` · ${analysis.company_name}` : ""}
                </h2>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <Badge>{analysis.band}</Badge>
                  <Badge>{analysis.decision}</Badge>
                  <span className="text-xs text-gray-500">Confidence: {analysis.confidence}</span>
                  {!analysis.hard_ok && <span className="text-xs font-medium text-coral">A mandatory requirement is unmet</span>}
                </div>
              </div>
              <div className="flex gap-6">
                <ScoreDial value={analysis.match_score} label="Job match" />
                {analysis.ats_score != null && <ScoreDial value={analysis.ats_score} label="ATS score" />}
                {analysis.quality_score != null && <ScoreDial value={analysis.quality_score} label="CV quality" />}
              </div>
            </div>
          </Card>

          {analysis.readiness_score != null && (
            <Alert kind={analysis.readiness_score >= 80 ? "success" : analysis.readiness_score >= 45 ? "info" : "error"}>
              <span className="font-semibold">Application readiness — {analysis.readiness_label} ({Math.round(analysis.readiness_score)}%).</span>{" "}
              {analysis.recommended_action}
            </Alert>
          )}
        </>
      )}

      {step === 1 && analysis && (
        <>
          <Card>
            <h2 className="mb-3 font-semibold">Score breakdown</h2>
            <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
              {Object.entries(analysis.sub_scores).map(([k, v]) => (
                <div key={k} className="rounded-lg bg-gray-50 px-3 py-2 text-sm">
                  <div className="text-gray-500">{SUB_SCORE_LABELS[k] || k}</div>
                  <div className={`font-semibold ${scoreColor(v)}`}>{Math.round(v)}%</div>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <div className="grid gap-6 md:grid-cols-3">
              <RequirementList title="Strong matches" tone="green" items={analysis.strong_matches} />
              <RequirementList title="Partial matches" tone="yellow" items={analysis.partial_matches} />
              <RequirementList title="Missing requirements" tone="red" items={analysis.missing_requirements} />
            </div>
            <p className="mt-4 text-xs text-gray-400">
              &ldquo;Not found in your CV&rdquo; means our records don&apos;t show it — not that you lack it. If you do
              have it, add it to your <Link href="/profile" className="underline">profile</Link> so future CVs reflect it truthfully.
            </p>
          </Card>

          {analysis.quality_suggestions && analysis.quality_suggestions.length > 0 && (
            <Card>
              <h2 className="mb-2 font-semibold">CV quality suggestions</h2>
              <ul className="list-disc space-y-1 pl-5 text-sm text-gray-700">
                {analysis.quality_suggestions.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </Card>
          )}

          <div className="flex justify-end">
            <Button onClick={() => setStep(2)}>Continue to improve &amp; design →</Button>
          </div>
        </>
      )}

      {step === 2 && draftCv && (
        <>
          <Card accent={violations.length ? "coral" : "teal"}>
            <h2 className="mb-2 font-semibold">Fact check</h2>
            {violations.length === 0 ? (
              <Alert kind="success">No unsupported claims found — everything in this draft comes from your real profile.</Alert>
            ) : (
              <>
                <Alert kind="error">
                  Some content couldn&apos;t be verified against your profile. Edit the fields below to remove or correct
                  it before generating your CV — nothing here should be invented.
                </Alert>
                <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-coral">
                  {violations.map((v, i) => <li key={i}>{v}</li>)}
                </ul>
              </>
            )}
          </Card>

          <Card>
            <h2 className="mb-3 font-semibold">Edit your draft CV</h2>
            <Field label="Professional summary" hint="Rewritten from your real profile — edit the wording, not the facts">
              <Textarea rows={4} value={draftCv.summary} onChange={(e) => updateSummary(e.target.value)} />
            </Field>
            <div className="mt-4">
              <Field label="Skills (comma-separated)" hint="Reordered to match this job — only skills already on your profile">
                <Textarea rows={2} value={skillsText} onChange={(e) => setSkillsText(e.target.value)} onBlur={commitSkills} />
              </Field>
            </div>
            {draftCv.experience.length > 0 && (
              <div className="mt-5">
                <h3 className="mb-2 text-sm font-semibold text-gray-700">Work experience (from your profile)</h3>
                <div className="space-y-3">
                  {draftCv.experience.map((exp, i) => (
                    <div key={i} className="rounded-lg border border-gray-200 p-3 text-sm">
                      <div className="font-medium">{exp.position} — {exp.employer}</div>
                      <div className="mt-1 text-xs text-gray-500">
                        {exp.start_date || "?"} – {exp.is_current ? "Present" : exp.end_date || "?"}
                      </div>
                      {exp.responsibilities != null && (
                        <p className="mt-2 text-gray-700">{String(exp.responsibilities)}</p>
                      )}
                      {exp.achievements != null && String(exp.achievements).trim() && (
                        <p className="mt-1 text-gray-700"><span className="font-medium">Achievements:</span> {String(exp.achievements)}</p>
                      )}
                    </div>
                  ))}
                </div>
                <p className="mt-2 text-xs text-gray-400">
                  To change these, update your <Link href="/profile" className="underline">profile</Link> — every tailored CV is
                  built from that record, so an edit there flows into every future CV too.
                </p>
              </div>
            )}
          </Card>

          <Card>
            <h2 className="mb-3 font-semibold">Choose a CV design</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {(templates.length ? templates : []).map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTemplate(t.id)}
                  className={`rounded-xl border p-4 text-left transition ${
                    template === t.id ? "border-brand bg-brand/5 ring-2 ring-brand/30" : "border-gray-200 hover:border-brand/40"
                  }`}
                >
                  <div className="font-semibold text-navy">{t.label}</div>
                  <div className="mt-1 text-xs text-gray-500">{t.description}</div>
                </button>
              ))}
            </div>
          </Card>

          <div className="flex justify-between">
            <Button variant="ghost" onClick={() => setStep(1)}>← Back to match report</Button>
            <Button onClick={generateCv} loading={busy === "cv"}>
              {busy === "cv" ? "Generating…" : "Generate my tailored CV"}
            </Button>
          </div>
        </>
      )}

      {step === 3 && analysis && (
        <>
          {cvVersion && (
            <Card accent="teal">
              <h2 className="mb-2 font-semibold">Your tailored CV is ready</h2>
              <div className="text-sm text-gray-600">
                {cvVersion.label} — ATS score {cvVersion.ats_score != null ? `${Math.round(cvVersion.ats_score)}%` : "—"} · truthfulness{" "}
                {cvVersion.truthfulness_ok ? "verified ✅" : "flagged ⚠️"}
              </div>
              <div className="mt-3 flex flex-wrap gap-4 text-sm">
                <button onClick={() => api.download(`/cv-versions/${cvVersion.id}/download?fmt=pdf`, `${cvVersion.label}.pdf`)} className="font-medium text-brand hover:underline">
                  Download CV (PDF)
                </button>
                <button onClick={() => api.download(`/cv-versions/${cvVersion.id}/download?fmt=docx`, `${cvVersion.label}.docx`)} className="font-medium text-brand hover:underline">
                  Download CV (Word)
                </button>
              </div>
            </Card>
          )}

          <Card>
            <h2 className="mb-3 font-semibold">Cover letter</h2>
            {!coverLetter ? (
              <Button variant="ghost" onClick={generateCoverLetter} loading={busy === "letter"}>
                {busy === "letter" ? "Generating…" : "Generate cover letter"}
              </Button>
            ) : (
              <div className="flex flex-wrap gap-4 text-sm">
                <button onClick={() => api.download(`/cover-letters/${coverLetter.id}/download?fmt=pdf`, `${coverLetter.label}.pdf`)} className="font-medium text-brand hover:underline">
                  Download cover letter (PDF)
                </button>
                <button onClick={() => api.download(`/cover-letters/${coverLetter.id}/download?fmt=docx`, `${coverLetter.label}.docx`)} className="font-medium text-brand hover:underline">
                  Download cover letter (Word)
                </button>
              </div>
            )}
          </Card>

          <Card>
            <h2 className="mb-3 font-semibold">Interview preparation</h2>
            {!prep ? (
              <Button variant="ghost" onClick={generatePrep} loading={busy === "prep"}>
                {busy === "prep" ? "Preparing…" : "Generate interview prep"}
              </Button>
            ) : (
              <div className="space-y-4 text-sm">
                <PrepList title="Likely questions" items={prep.content.questions} />
                <PrepList title="Talking points" items={prep.content.talking_points} />
                {prep.content.watch_outs?.length > 0 && <PrepList title="Watch-outs" items={prep.content.watch_outs} />}
                <PrepList title="Tips" items={prep.content.tips} />
              </div>
            )}
          </Card>

          <Card>
            <p className="text-sm text-gray-600">
              This job has been added to your <Link href="/tailor/applications" className="font-semibold text-brand hover:underline">application tracker</Link> —
              update its status once you&apos;ve applied.
            </p>
          </Card>

          <div className="flex justify-between">
            <Button variant="ghost" onClick={() => setStep(2)}>← Back to improve &amp; design</Button>
            <Button variant="ghost" onClick={() => { setStep(0); setAnalysis(null); setDraftCv(null); setCvVersion(null); setCoverLetter(null); setPrep(null); setDesc(""); setTitle(""); setCompany(""); }}>
              Tailor for another job
            </Button>
          </div>
        </>
      )}

      {busy === "analyze" && step === 0 && <Spinner label="Analysing the job advert…" />}
    </div>
  );
}

function PrepList({ title, items }: { title: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div>
      <div className="mb-1 font-medium text-gray-700">{title}</div>
      <ul className="list-disc space-y-1 pl-5 text-gray-600">
        {items.map((x, i) => <li key={i}>{x}</li>)}
      </ul>
    </div>
  );
}

export default function TailorPage() {
  return (
    <Guard>
      <TailorInner />
    </Guard>
  );
}
