"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Button, Alert, Spinner, Badge } from "@/components/ui";
import type { MatchDetail, CVVersion } from "@/lib/types";

function MatchDetailInner() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [m, setM] = useState<MatchDetail | null>(null);
  const [cv, setCv] = useState<CVVersion | null>(null);
  const [prep, setPrep] = useState<{ content: Record<string, string[] | string> } | null>(null);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    api.get<MatchDetail>(`/matches/${id}`).then(setM).catch((e) => setErr(e.message));
  }, [id]);

  async function act(kind: "cv" | "cover" | "apply" | "prep") {
    setBusy(kind); setErr(""); setMsg("");
    try {
      if (kind === "cv") {
        setCv(await api.post<CVVersion>(`/matches/${id}/generate-cv`));
        setMsg("Tailored CV generated.");
      } else if (kind === "cover") {
        await api.post(`/matches/${id}/generate-cover-letter`);
        setMsg("Cover letter generated (see Applications / CV section).");
      } else if (kind === "prep") {
        setPrep(await api.post(`/matches/${id}/interview-prep`));
        setMsg("Interview prep ready — see below.");
      } else {
        const app = await api.post<{ id: string }>(`/matches/${id}/prepare-application`);
        router.push(`/applications/${app.id}`);
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy("");
    }
  }

  if (err && !m) return <Alert kind="error">{err}</Alert>;
  if (!m) return <Spinner />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{m.vacancy_title}</h1>
        <p className="text-gray-500">{m.company_name}</p>
      </div>
      {msg && <Alert kind="success">{msg}</Alert>}
      {err && <Alert kind="error">{err}</Alert>}

      <div className="flex flex-wrap items-center gap-3">
        <span className="text-4xl font-bold">{Math.round(m.score)}%</span>
        <Badge>{m.band}</Badge>
        <Badge>{m.decision}</Badge>
        <span className="text-sm text-gray-500">Confidence: {m.confidence}</span>
        {!m.hard_ok && <Badge>Hard requirement unmet</Badge>}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <h2 className="mb-3 font-semibold text-green-700">Why you match</h2>
          {m.reasons.length ? (
            <ul className="list-disc space-y-1 pl-5 text-sm">{m.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
          ) : <p className="text-sm text-gray-400">—</p>}
        </Card>
        <Card>
          <h2 className="mb-3 font-semibold text-orange-700">Gaps to be aware of</h2>
          {m.gaps.length ? (
            <ul className="list-disc space-y-1 pl-5 text-sm">{m.gaps.map((g, i) => <li key={i}>{g}</li>)}</ul>
          ) : <p className="text-sm text-gray-400">None flagged.</p>}
        </Card>
      </div>

      <Card>
        <h2 className="mb-3 font-semibold">Score breakdown</h2>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          {Object.entries(m.sub_scores).map(([k, v]) => (
            <div key={k} className="rounded-lg bg-gray-50 px-3 py-2 text-sm">
              <div className="capitalize text-gray-500">{k}</div>
              <div className="font-semibold">{Math.round(v)}%</div>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 font-semibold">Take action</h2>
        <div className="flex flex-wrap gap-3">
          <Button onClick={() => act("cv")} disabled={!!busy}>{busy === "cv" ? "Generating…" : "Generate tailored CV"}</Button>
          <Button onClick={() => act("cover")} variant="ghost" disabled={!!busy}>{busy === "cover" ? "Generating…" : "Generate cover letter"}</Button>
          <Button onClick={() => act("apply")} variant="ghost" disabled={!!busy || m.decision === "DO_NOT_APPLY"}>
            {busy === "apply" ? "Preparing…" : "Prepare application"}
          </Button>
          <Button onClick={() => act("prep")} variant="ghost" disabled={!!busy}>
            {busy === "prep" ? "Preparing…" : "Interview prep"}
          </Button>
        </div>
        {cv && (
          <div className="mt-3 text-sm">
            Tailored CV ready — ATS score {cv.ats_score}% · truthfulness {cv.truthfulness_ok ? "verified ✅" : "check ⚠️"}.{" "}
            <button onClick={() => api.download(`/cv-versions/${cv.id}/download?fmt=pdf`, `${cv.label}.pdf`)} className="text-brand hover:underline">
              Download PDF
            </button>
          </div>
        )}
      </Card>

      {prep && (
        <Card>
          <h2 className="mb-3 font-semibold">Interview preparation</h2>
          <div className="space-y-4 text-sm">
            <PrepList title="Likely questions" items={prep.content.questions as string[]} />
            <PrepList title="Talking points" items={prep.content.talking_points as string[]} />
            {(prep.content.watch_outs as string[])?.length > 0 && (
              <PrepList title="Watch-outs" items={prep.content.watch_outs as string[]} />
            )}
            <PrepList title="Tips" items={prep.content.tips as string[]} />
          </div>
        </Card>
      )}
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

export default function MatchDetailPage() {
  return (
    <Guard>
      <MatchDetailInner />
    </Guard>
  );
}
