"use client";

import { useEffect, useState } from "react";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Field, Input, Button, Alert, Spinner } from "@/components/ui";

interface Doc { id: string; label: string; ats_score?: number | null; truthfulness_ok?: boolean }
interface TailorResult { cv_version: Doc; cover_letter: Doc }

function TailorInner() {
  const [company, setCompany] = useState("");
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [res, setRes] = useState<TailorResult | null>(null);

  useEffect(() => {
    const p = new URLSearchParams(window.location.search).get("company");
    if (p) setCompany(p);
  }, []);

  async function generate() {
    setBusy(true); setErr(""); setRes(null);
    try {
      const r = await api.post<TailorResult>("/tailor", {
        job_title: title || null,
        company_name: company || null,
        job_description: desc || null,
      });
      setRes(r);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not generate. Is your subscription active?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Tailor my CV</h1>
        <p className="text-sm text-gray-500">
          Pick an employer or paste a job ad, and we&apos;ll generate a CV and cover letter tailored to it —
          built only from your real profile, never invented. Then apply on the employer&apos;s page.
        </p>
      </div>

      {err && <Alert kind="error">{err}</Alert>}

      <Card>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Company (optional)">
            <Input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="e.g. Eskom" />
          </Field>
          <Field label="Job title">
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Operations Manager" />
          </Field>
        </div>
        <div className="mt-4">
          <label className="mb-1 block text-sm font-medium text-gray-700">Paste the job advert (optional but recommended)</label>
          <textarea
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            rows={8}
            placeholder="Paste the job description here — the more detail, the better the tailoring."
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
          />
        </div>
        <div className="mt-4">
          <Button onClick={generate} disabled={busy}>
            {busy ? "Generating…" : "Generate tailored CV & cover letter"}
          </Button>
        </div>
      </Card>

      {busy && <Spinner />}

      {res && (
        <Card>
          <h2 className="mb-3 text-lg font-semibold">Your tailored documents are ready</h2>
          <div className="space-y-4">
            <div>
              <div className="font-medium">{res.cv_version.label}</div>
              {typeof res.cv_version.ats_score === "number" && (
                <div className="text-xs text-gray-500">ATS compatibility: {Math.round(res.cv_version.ats_score)}%</div>
              )}
              <div className="mt-1 flex gap-3 text-sm">
                <button onClick={() => api.download(`/cv-versions/${res.cv_version.id}/download?fmt=pdf`, res.cv_version.label + ".pdf")} className="text-brand hover:underline">Download CV (PDF)</button>
                <button onClick={() => api.download(`/cv-versions/${res.cv_version.id}/download?fmt=docx`, res.cv_version.label + ".docx")} className="text-brand hover:underline">Download CV (Word)</button>
              </div>
            </div>
            <div>
              <div className="font-medium">{res.cover_letter.label}</div>
              <div className="mt-1 flex gap-3 text-sm">
                <button onClick={() => api.download(`/cover-letters/${res.cover_letter.id}/download?fmt=pdf`, res.cover_letter.label + ".pdf")} className="text-brand hover:underline">Download cover letter (PDF)</button>
                <button onClick={() => api.download(`/cover-letters/${res.cover_letter.id}/download?fmt=docx`, res.cover_letter.label + ".docx")} className="text-brand hover:underline">Download cover letter (Word)</button>
              </div>
            </div>
          </div>
          <p className="mt-4 text-xs text-gray-500">Review everything before you send it. Apply on the employer&apos;s official careers page (see Companies).</p>
        </Card>
      )}
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
