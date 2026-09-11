"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Alert, Spinner, Badge } from "@/components/ui";
import type { JobAnalysisDetail } from "@/lib/types";

const SUB_SCORE_LABELS: Record<string, string> = {
  qualification: "Qualifications",
  experience: "Experience",
  technical_skill: "Technical skills",
  industry: "Industry fit",
  certification: "Certifications",
  keyword: "Keyword alignment",
  responsibility: "Responsibilities",
};

interface InterviewPrepDoc {
  content: { questions: string[]; talking_points: string[]; watch_outs: string[]; tips: string[] };
}

function RequirementList({ title, items, tone }: { title: string; items: { text: string; note: string }[]; tone: "green" | "yellow" | "red" }) {
  const toneCls = { green: "text-green-700", yellow: "text-yellow-700", red: "text-coral" }[tone];
  return (
    <div>
      <h3 className={`mb-2 text-sm font-semibold ${toneCls}`}>{title} ({items.length})</h3>
      {items.length === 0 ? <p className="text-sm text-gray-400">None.</p> : (
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

function ApplicationDetailInner() {
  const { id } = useParams<{ id: string }>();
  const [a, setA] = useState<JobAnalysisDetail | null>(null);
  const [prep, setPrep] = useState<InterviewPrepDoc | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get<JobAnalysisDetail>(`/tailor/applications/${id}`).then(setA).catch((e) => setErr(e.message));
    api.get<InterviewPrepDoc>(`/tailor/${id}/interview-prep`).then(setPrep).catch(() => {});
  }, [id]);

  if (err) return <Alert kind="error">{err}</Alert>;
  if (!a) return <Spinner />;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/tailor/applications" className="text-sm text-brand hover:underline">← Back to my applications</Link>
        <h1 className="mt-2 text-2xl font-bold text-navy">{a.job_title}</h1>
        <p className="text-gray-500">{a.company_name || "Company not specified"}</p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Badge>{a.status}</Badge>
          <Badge>{a.band}</Badge>
          <span className="text-sm text-gray-500">Match {Math.round(a.match_score)}%</span>
          {a.ats_score != null && <span className="text-sm text-gray-500">· ATS {Math.round(a.ats_score)}%</span>}
          {a.quality_score != null && <span className="text-sm text-gray-500">· Quality {Math.round(a.quality_score)}%</span>}
        </div>
      </div>

      {a.readiness_score != null && (
        <Alert kind={a.readiness_score >= 80 ? "success" : a.readiness_score >= 45 ? "info" : "error"}>
          <span className="font-semibold">{a.readiness_label} ({Math.round(a.readiness_score)}%).</span> {a.recommended_action}
        </Alert>
      )}

      <Card>
        <h2 className="mb-3 font-semibold">Score breakdown</h2>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          {Object.entries(a.sub_scores).map(([k, v]) => (
            <div key={k} className="rounded-lg bg-gray-50 px-3 py-2 text-sm">
              <div className="text-gray-500">{SUB_SCORE_LABELS[k] || k}</div>
              <div className="font-semibold">{Math.round(v)}%</div>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <div className="grid gap-6 md:grid-cols-3">
          <RequirementList title="Strong matches" tone="green" items={a.strong_matches} />
          <RequirementList title="Partial matches" tone="yellow" items={a.partial_matches} />
          <RequirementList title="Missing requirements" tone="red" items={a.missing_requirements} />
        </div>
      </Card>

      {(a.cv_version_id || a.cover_letter_id) && (
        <Card>
          <h2 className="mb-3 font-semibold">Documents</h2>
          <div className="flex flex-wrap gap-4 text-sm">
            {a.cv_version_id && (
              <>
                <button onClick={() => api.download(`/cv-versions/${a.cv_version_id}/download?fmt=pdf`, `${a.job_title}_CV.pdf`)} className="font-medium text-brand hover:underline">
                  Download CV (PDF)
                </button>
                <button onClick={() => api.download(`/cv-versions/${a.cv_version_id}/download?fmt=docx`, `${a.job_title}_CV.docx`)} className="font-medium text-brand hover:underline">
                  Download CV (Word)
                </button>
              </>
            )}
            {a.cover_letter_id && (
              <>
                <button onClick={() => api.download(`/cover-letters/${a.cover_letter_id}/download?fmt=pdf`, `${a.job_title}_CoverLetter.pdf`)} className="font-medium text-brand hover:underline">
                  Download cover letter (PDF)
                </button>
                <button onClick={() => api.download(`/cover-letters/${a.cover_letter_id}/download?fmt=docx`, `${a.job_title}_CoverLetter.docx`)} className="font-medium text-brand hover:underline">
                  Download cover letter (Word)
                </button>
              </>
            )}
          </div>
        </Card>
      )}

      {prep && (
        <Card>
          <h2 className="mb-3 font-semibold">Interview preparation</h2>
          <div className="space-y-4 text-sm">
            {[["Likely questions", prep.content.questions], ["Talking points", prep.content.talking_points],
              ["Watch-outs", prep.content.watch_outs], ["Tips", prep.content.tips]].map(([t, items]) => (
              (items as string[])?.length > 0 && (
                <div key={t as string}>
                  <div className="mb-1 font-medium text-gray-700">{t}</div>
                  <ul className="list-disc space-y-1 pl-5 text-gray-600">
                    {(items as string[]).map((x, i) => <li key={i}>{x}</li>)}
                  </ul>
                </div>
              )
            ))}
          </div>
        </Card>
      )}

      {a.notes && (
        <Card>
          <h2 className="mb-2 font-semibold">Notes</h2>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{a.notes}</p>
        </Card>
      )}
    </div>
  );
}

export default function ApplicationDetailPage() {
  return (
    <Guard>
      <ApplicationDetailInner />
    </Guard>
  );
}
