"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Alert, Spinner, Badge, Button, Input } from "@/components/ui";
import type { Application } from "@/lib/types";

function ApplicationDetailInner() {
  const { id } = useParams<{ id: string }>();
  const [app, setApp] = useState<Application | null>(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setApp(await api.get<Application>(`/applications/${id}`));
  }, [id]);
  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, [load]);

  async function doAction(path: string, body?: unknown) {
    setBusy(true); setErr(""); setMsg("");
    try {
      await api.post(`/applications/${id}/${path}`, body);
      await load();
      setMsg("Updated.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  async function fillAnswer(answerId: string, value: string) {
    await api.put(`/applications/${id}/answers/${answerId}`, { value });
    await load();
  }

  if (err && !app) return <Alert kind="error">{err}</Alert>;
  if (!app) return <Spinner />;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">Application</h1>
        <Badge>{app.status}</Badge>
      </div>
      {msg && <Alert kind="success">{msg}</Alert>}
      {err && <Alert kind="error">{err}</Alert>}

      {app.action_required_note && <Alert kind="info">{app.action_required_note}</Alert>}

      <Card>
        <h2 className="mb-3 font-semibold">Actions</h2>
        <div className="flex flex-wrap gap-3">
          {app.status === "AWAITING_APPROVAL" && (
            <Button onClick={() => doAction("approve")} disabled={busy}>Approve &amp; authorise</Button>
          )}
          {["AWAITING_APPROVAL", "CANDIDATE_ACTION_REQUIRED", "APPLICATION_PREPARED"].includes(app.status) && (
            <>
              <Button onClick={() => doAction("auto-submit")} disabled={busy}>Try automated submission</Button>
              <Button variant="ghost" onClick={() => doAction("mark-submitted")} disabled={busy}>Mark as submitted</Button>
            </>
          )}
          {app.application_url && (
            <a href={app.application_url} target="_blank" rel="noreferrer">
              <Button variant="ghost">Open employer application ↗</Button>
            </a>
          )}
          {["SUBMITTED", "INTERVIEW"].includes(app.status) && (
            <>
              <Button variant="ghost" onClick={() => doAction("status", { status: "INTERVIEW" })} disabled={busy}>Mark interview</Button>
              <Button variant="ghost" onClick={() => doAction("status", { status: "OFFER" })} disabled={busy}>Mark offer</Button>
            </>
          )}
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 font-semibold">Application answers</h2>
        <ul className="space-y-3">
          {(app.answers || []).map((a) => (
            <li key={a.id} className="text-sm">
              <div className="font-medium text-gray-700">{a.question}</div>
              {a.is_unknown ? (
                <UnknownAnswer onSave={(v) => fillAnswer(a.id, v)} />
              ) : (
                <div className="text-gray-600">
                  {a.answer} <span className="text-xs text-gray-400">({a.source})</span>
                </div>
              )}
            </li>
          ))}
        </ul>
      </Card>

      <Card>
        <h2 className="mb-3 font-semibold">History (audit trail)</h2>
        <ul className="space-y-1 text-sm text-gray-600">
          {(app.events || []).map((e) => (
            <li key={e.id}>
              <span className="text-gray-400">{new Date(e.created_at).toLocaleString()}</span> — {e.event_type}
              {e.status_to && <> → <Badge>{e.status_to}</Badge></>} {e.detail && <span className="text-gray-500">· {e.detail}</span>}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

function UnknownAnswer({ onSave }: { onSave: (v: string) => Promise<void> }) {
  const [v, setV] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="mt-1 flex items-center gap-2">
      <span className="rounded bg-yellow-100 px-2 py-0.5 text-xs text-yellow-800">Needs your input</span>
      <Input value={v} onChange={(e) => setV(e.target.value)} placeholder="Your answer" className="max-w-xs" />
      <Button
        variant="ghost"
        disabled={busy || !v}
        onClick={async () => { setBusy(true); try { await onSave(v); } finally { setBusy(false); } }}
      >
        Save
      </Button>
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
