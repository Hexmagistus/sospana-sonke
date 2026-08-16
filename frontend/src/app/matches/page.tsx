"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Button, Alert, Spinner, Badge } from "@/components/ui";
import type { Match } from "@/lib/types";

function MatchesInner() {
  const [matches, setMatches] = useState<Match[]>([]);
  const [err, setErr] = useState("");
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(true);

  async function load() {
    setMatches(await api.get<Match[]>("/matches"));
    setLoading(false);
  }
  useEffect(() => {
    load().catch((e) => { setErr(e.message); setLoading(false); });
  }, []);

  async function run() {
    setRunning(true); setErr("");
    try {
      await api.post("/matches/run");
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Matching failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Vacancy matches</h1>
        <Button onClick={run} disabled={running}>{running ? "Finding…" : "Find new matches"}</Button>
      </div>
      {err && <Alert kind="error">{err}</Alert>}
      {loading ? (
        <Spinner />
      ) : matches.length === 0 ? (
        <Card><p className="text-sm text-gray-500">No matches yet. Complete your profile, then click “Find new matches”.</p></Card>
      ) : (
        <div className="space-y-3">
          {matches.map((m) => (
            <Card key={m.id}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="font-medium">{m.vacancy_title || "Vacancy"}</div>
                  <div className="text-sm text-gray-500">{m.company_name}</div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-2xl font-semibold">{Math.round(m.score)}%</span>
                  <Badge>{m.band}</Badge>
                  <Badge>{m.decision}</Badge>
                  <Link href={`/matches/${m.id}`}><Button variant="ghost">View</Button></Link>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

export default function MatchesPage() {
  return (
    <Guard>
      <MatchesInner />
    </Guard>
  );
}
