"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Alert, Spinner, Badge, Button } from "@/components/ui";
import type { Application } from "@/lib/types";

function ApplicationsInner() {
  const [apps, setApps] = useState<Application[]>([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Application[]>("/applications")
      .then((a) => { setApps(a); setLoading(false); })
      .catch((e) => { setErr(e.message); setLoading(false); });
  }, []);

  if (loading) return <Spinner />;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Applications</h1>
      {err && <Alert kind="error">{err}</Alert>}
      {apps.length === 0 ? (
        <Card><p className="text-sm text-gray-500">No applications yet. Prepare one from a match.</p></Card>
      ) : (
        <div className="space-y-3">
          {apps.map((a) => (
            <Card key={a.id}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="font-medium">Application</div>
                  <div className="text-xs text-gray-500">Mode: {a.mode} · Created {new Date(a.created_at).toLocaleDateString()}</div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge>{a.status}</Badge>
                  <Link href={`/applications/${a.id}`}><Button variant="ghost">Open</Button></Link>
                </div>
              </div>
            </Card>
          ))}
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
