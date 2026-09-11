"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Button, Alert, Spinner, Badge, Select, Textarea } from "@/components/ui";
import type { JobAnalysisSummary } from "@/lib/types";

const STATUSES = ["PREPARING", "APPLIED", "INTERVIEW", "ASSESSMENT", "OFFER", "REJECTED", "WITHDRAWN"];

const STATUS_LABEL: Record<string, string> = {
  PREPARING: "Preparing",
  APPLIED: "Applied",
  INTERVIEW: "Interview",
  ASSESSMENT: "Assessment",
  OFFER: "Offer",
  REJECTED: "Rejected",
  WITHDRAWN: "Withdrawn",
};

function Row({ app, onChange }: { app: JobAnalysisSummary; onChange: (a: JobAnalysisSummary) => void }) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState(app.status);
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  async function save() {
    setSaving(true); setErr("");
    try {
      const updated = await api.put<JobAnalysisSummary>(`/tailor/applications/${app.id}`, { status, notes });
      onChange(updated);
      setOpen(false);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not update.");
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!window.confirm(`Remove ${app.job_title}${app.company_name ? " at " + app.company_name : ""} from your tracker?`)) return;
    try {
      await api.del(`/tailor/applications/${app.id}`);
      onChange({ ...app, status: "__deleted__" });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not remove.");
    }
  }

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link href={`/tailor/applications/${app.id}`} className="font-semibold text-navy hover:underline">
            {app.job_title}
          </Link>
          <div className="text-sm text-gray-500">{app.company_name || "Company not specified"}</div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">Match {Math.round(app.match_score)}%</span>
          <Badge>{STATUS_LABEL[app.status] || app.status}</Badge>
          <Button size="sm" variant="ghost" onClick={() => setOpen((v) => !v)}>{open ? "Close" : "Update"}</Button>
          <Button size="sm" variant="danger" onClick={remove}>Remove</Button>
        </div>
      </div>

      {open && (
        <div className="mt-4 space-y-3 border-t border-gray-100 pt-4">
          {err && <Alert kind="error">{err}</Alert>}
          <div className="grid gap-3 sm:grid-cols-2">
            <Select value={status} onChange={(e) => setStatus(e.target.value)}>
              {STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
            </Select>
          </div>
          <Textarea rows={2} placeholder="Notes (optional)" value={notes} onChange={(e) => setNotes(e.target.value)} />
          <Button size="sm" onClick={save} loading={saving}>{saving ? "Saving…" : "Save"}</Button>
        </div>
      )}
    </Card>
  );
}

function ApplicationsInner() {
  const [apps, setApps] = useState<JobAnalysisSummary[] | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get<JobAnalysisSummary[]>("/tailor/applications").then(setApps).catch((e) => setErr(e.message));
  }, []);

  function handleChange(updated: JobAnalysisSummary) {
    setApps((prev) => {
      if (!prev) return prev;
      if (updated.status === "__deleted__") return prev.filter((a) => a.id !== updated.id);
      return prev.map((a) => (a.id === updated.id ? updated : a));
    });
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-navy">My job applications</h1>
          <p className="text-gray-500">Every job you&apos;ve analysed and tailored a CV for, in one place.</p>
        </div>
        <Link href="/tailor"><Button variant="ghost">+ Tailor for a new job</Button></Link>
      </div>

      {err && <Alert kind="error">{err}</Alert>}
      {!apps ? (
        <Spinner />
      ) : apps.length === 0 ? (
        <Card>
          <p className="text-sm text-gray-500">
            No jobs analysed yet. Head to <Link href="/tailor" className="text-brand hover:underline">Build my job-aligned CV</Link> to get started.
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {apps.map((a) => <Row key={a.id} app={a} onChange={handleChange} />)}
        </div>
      )}
    </div>
  );
}

export default function ApplicationsPage() {
  return (
    <Guard>
      <ApplicationsInner />
    </Guard>
  );
}
