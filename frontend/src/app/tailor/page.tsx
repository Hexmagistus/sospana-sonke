"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Field, Input, Button, Alert, Spinner } from "@/components/ui";
import { Banner } from "@/components/Banner";

interface Doc { id: string; label: string; ats_score?: number | null; truthfulness_ok?: boolean }
interface TailorResult { cv_version: Doc; cover_letter: Doc }

// CV tailoring is temporarily switched off while we focus on getting people
// straight in front of employers and their open vacancies. Flip this back to
// true to re-enable the feature — nothing else needs to change.
const CV_TAILORING_ENABLED = false;

function TailorInner() {
  const [company, setCompany] = useState("");
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [res, setRes] = useState<TailorResult | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const c = params.get("company");
    if (c) setCompany(c);
    const t = params.get("title");
    if (t) setTitle(t);
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
      setErr(e instanceof Error ? e.message : "Could not generate. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <Banner
        variant="tailor"
        eyebrow="Apply smarter"
        title="Tailor my CV"
        subtitle="Pick an employer or paste a job ad, and we'll generate a CV and cover letter tailored to it — built only from your real profile, never invented. Then apply on the employer's page."
      />

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

function TailorPaused() {
  return (
    <div className="mx-auto max-w-xl py-16 text-center">
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gold/15 text-3xl">🛠️</div>
      <h1 className="text-2xl font-bold text-navy">CV tailoring is paused for now</h1>
      <p className="mt-3 text-gray-600">
        We&apos;ve switched this off temporarily while we focus on getting you in front of employers. In the
        meantime, explore{" "}
        <Link href="/jobs" className="font-semibold text-brand-dark underline">open vacancies</Link> or the{" "}
        <Link href="/companies" className="font-semibold text-brand-dark underline">companies directory</Link>{" "}
        and apply direct on each employer&apos;s official page.
      </p>
    </div>
  );
}

export default function TailorPage() {
  return (
    <Guard>
      {CV_TAILORING_ENABLED ? <TailorInner /> : <TailorPaused />}
    </Guard>
  );
}
