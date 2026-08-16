"use client";

import { useEffect, useRef, useState } from "react";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Button, Alert, Spinner, Badge } from "@/components/ui";

interface CV {
  id: string;
  original_filename: string;
  extension: string;
  parse_status: string;
  parse_error: string | null;
  ai_model: string | null;
  created_at: string;
}

function CVInner() {
  const [cvs, setCvs] = useState<CV[]>([]);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    setCvs(await api.get<CV[]>("/cv"));
  }
  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, []);

  async function upload() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setBusy(true); setErr(""); setMsg("");
    try {
      await api.upload("/cv", file);
      setMsg("CV uploaded and parsed. Review the extracted data below, then import it into your profile.");
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function applyToProfile(id: string) {
    setErr(""); setMsg("");
    try {
      const r = await api.post<{ skills_added: number; education_added: number; work_experience_added: number }>(
        `/cv/${id}/apply-to-profile`, {}
      );
      setMsg(`Imported ${r.skills_added} skills, ${r.education_added} education and ${r.work_experience_added} experience entries as unconfirmed — confirm them on your profile.`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Apply failed");
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">My CV</h1>
      {msg && <Alert kind="success">{msg}</Alert>}
      {err && <Alert kind="error">{err}</Alert>}

      <Card>
        <h2 className="mb-2 text-lg font-semibold">Upload a CV</h2>
        <p className="mb-3 text-sm text-gray-500">PDF, DOCX or TXT. Your original is stored unchanged.</p>
        <div className="flex items-center gap-3">
          <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" className="text-sm" />
          <Button onClick={upload} disabled={busy}>{busy ? "Uploading…" : "Upload"}</Button>
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 text-lg font-semibold">Uploaded CVs</h2>
        {cvs.length === 0 ? (
          <p className="text-sm text-gray-400">No CVs uploaded yet.</p>
        ) : (
          <ul className="space-y-2">
            {cvs.map((cv) => (
              <li key={cv.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-gray-100 px-3 py-2 text-sm">
                <span className="flex items-center gap-2">
                  {cv.original_filename} <Badge>{cv.parse_status}</Badge>
                  {cv.ai_model && <span className="text-xs text-gray-400">({cv.ai_model})</span>}
                </span>
                <span className="flex gap-3">
                  <button onClick={() => api.download(`/cv/${cv.id}/download`, cv.original_filename)} className="text-brand hover:underline">
                    Download original
                  </button>
                  {cv.parse_status === "parsed" && (
                    <button onClick={() => applyToProfile(cv.id)} className="text-brand hover:underline">
                      Import to profile
                    </button>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

export default function CVPage() {
  return (
    <Guard>
      <CVInner />
    </Guard>
  );
}
