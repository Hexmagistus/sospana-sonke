"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Card, Button, Alert, Spinner } from "@/components/ui";
import type { UploadedCv, CvApplyResult } from "@/lib/types";

const ACCEPT = ".pdf,.docx,.txt";
const MAX_BYTES = 10 * 1024 * 1024; // 10MB — matches the backend's upload size ceiling

const STATUS_LABEL: Record<UploadedCv["parse_status"], string> = {
  uploaded: "Uploading…",
  extracted: "Reading…",
  parsed: "Picked up ✓",
  failed: "Could not read",
};

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function summarize(r: CvApplyResult): string {
  const parts: string[] = [];
  if (r.skills_added) parts.push(`${r.skills_added} skill${r.skills_added === 1 ? "" : "s"}`);
  if (r.education_added) parts.push(`${r.education_added} education entr${r.education_added === 1 ? "y" : "ies"}`);
  if (r.work_experience_added) parts.push(`${r.work_experience_added} work experience entr${r.work_experience_added === 1 ? "y" : "ies"}`);
  if (r.certifications_added) parts.push(`${r.certifications_added} certification${r.certifications_added === 1 ? "" : "s"}`);
  if (r.profile_fields_filled.length) parts.push(`${r.profile_fields_filled.length} detail${r.profile_fields_filled.length === 1 ? "" : "s"} in "About you" (occupation, city, years of experience, links)`);
  if (parts.length === 0) return "We couldn't find anything new to add — your profile may already cover everything in this CV.";
  return `Picked up ${parts.join(", ")}. Review the “from CV” items and the About you section below, and correct anything that's off.`;
}

export function CvUpload({ onApplied }: { onApplied?: () => void }) {
  const [cvs, setCvs] = useState<UploadedCv[] | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  async function refresh() {
    setCvs(await api.get<UploadedCv[]>("/cv"));
  }
  useEffect(() => {
    refresh().catch((e) => setErr(e.message));
  }, []);

  async function handleFile(file: File) {
    setErr(""); setMsg("");
    const ext = file.name.split(".").pop()?.toLowerCase() || "";
    if (!["pdf", "docx", "txt"].includes(ext)) {
      setErr("Please upload a PDF, Word (.docx) or plain text CV.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setErr("That file is larger than 10MB — please upload a smaller CV.");
      return;
    }
    setBusy(true);
    try {
      const cv = await api.upload<UploadedCv>("/cv", file);
      await refresh();
      if (cv.parse_status === "parsed") {
        const result = await api.post<CvApplyResult>(`/cv/${cv.id}/apply-to-profile`, {});
        setMsg(summarize(result));
        onApplied?.();
      } else if (cv.parse_status === "failed") {
        setErr(cv.parse_error || "We couldn't read that CV. Try a different file, or add your details manually below.");
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Upload failed. Please try again.");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function reapply(id: string) {
    setBusy(true); setErr(""); setMsg("");
    try {
      const result = await api.post<CvApplyResult>(`/cv/${id}/apply-to-profile`, {});
      setMsg(summarize(result));
      onApplied?.();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not import from this CV.");
    } finally {
      setBusy(false);
    }
  }

  async function reparse(id: string) {
    setBusy(true); setErr(""); setMsg("");
    try {
      await api.post(`/cv/${id}/reparse`);
      await refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not re-read this CV.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    if (!window.confirm("Remove this uploaded CV? This only removes the original file — anything already added to your profile stays.")) return;
    try {
      await api.del(`/cv/${id}`);
      await refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not remove this file.");
    }
  }

  return (
    <Card accent="purple">
      <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-navy">
        <span aria-hidden="true">📤</span> Import from an existing CV
      </h2>
      <p className="mb-4 text-sm text-gray-500">
        Upload a CV you already have — we&apos;ll read it and automatically add your skills, education and experience
        below as unconfirmed suggestions. Nothing is treated as fact until you confirm it.
      </p>

      {err && <Alert kind="error">{err}</Alert>}
      {msg && <div className="mt-3"><Alert kind="success">{msg}</Alert></div>}

      <div
        onClick={() => !busy && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const file = e.dataTransfer.files?.[0];
          if (file) handleFile(file);
        }}
        className={`mt-3 flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-8 text-center transition ${
          dragOver ? "border-brand bg-brand/5" : "border-gray-300 hover:border-brand/50 hover:bg-gray-50"
        } ${busy ? "pointer-events-none opacity-60" : ""}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />
        {busy ? (
          <Spinner label="Reading your CV…" />
        ) : (
          <>
            <span className="text-2xl" aria-hidden="true">📄</span>
            <span className="text-sm font-medium text-navy">Click to upload, or drag and drop</span>
            <span className="text-xs text-gray-400">PDF, Word (.docx) or plain text — up to 10MB</span>
          </>
        )}
      </div>

      {cvs && cvs.length > 0 && (
        <div className="mt-4 space-y-2 border-t border-gray-100 pt-4">
          {cvs.map((cv) => (
            <div key={cv.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-gray-50/60 px-3 py-2 text-sm">
              <div className="min-w-0">
                <div className="truncate font-medium text-gray-800">{cv.original_filename}</div>
                <div className="text-xs text-gray-500">
                  {formatSize(cv.size_bytes)} · {STATUS_LABEL[cv.parse_status]}
                  {cv.parse_status === "failed" && cv.parse_error ? ` — ${cv.parse_error}` : ""}
                </div>
              </div>
              <div className="flex shrink-0 flex-wrap gap-3 text-xs">
                <button onClick={() => api.download(`/cv/${cv.id}/download`, cv.original_filename)} className="font-medium text-brand hover:underline">
                  Download
                </button>
                {cv.parse_status === "parsed" && (
                  <button onClick={() => reapply(cv.id)} className="font-medium text-brand hover:underline" disabled={busy}>
                    Import again
                  </button>
                )}
                {cv.parse_status === "failed" && (
                  <button onClick={() => reparse(cv.id)} className="font-medium text-brand hover:underline" disabled={busy}>
                    Retry
                  </button>
                )}
                <button onClick={() => remove(cv.id)} className="font-medium text-coral hover:underline">
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
