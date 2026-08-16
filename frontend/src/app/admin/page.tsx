"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Stat, Card, Alert, Spinner, Button } from "@/components/ui";
import type { AdminDashboard } from "@/lib/types";

function AdminInner() {
  const [d, setD] = useState<AdminDashboard | null>(null);
  const [err, setErr] = useState("");
  const [job, setJob] = useState("");

  async function load() {
    setD(await api.get<AdminDashboard>("/admin/dashboard"));
  }
  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, []);

  async function runJob(name: string) {
    setJob(name);
    try {
      await api.post(`/admin/jobs/${name}/run`);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Job failed");
    } finally {
      setJob("");
    }
  }

  if (err && !d) return <Alert kind="error">{err}</Alert>;
  if (!d) return <Spinner />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Admin dashboard</h1>
        <Link href="/admin/companies"><Button variant="ghost">Manage companies</Button></Link>
      </div>
      {err && <Alert kind="error">{err}</Alert>}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Registered candidates" value={d.registered_candidates} />
        <Stat label="Active subscriptions" value={d.active_subscriptions} />
        <Stat label="Paying subscriptions" value={d.paying_subscriptions} />
        <Stat label="Estimated MRR" value={`R${d.estimated_mrr_zar.toLocaleString()}`} />
        <Stat label="Companies" value={d.companies_total} hint={`${d.companies_active} active`} />
        <Stat label="Sources failing" value={d.sources_failing} />
        <Stat label="Open vacancies" value={d.vacancies_open} hint={`${d.vacancies_total} total`} />
        <Stat label="CVs generated" value={d.cv_versions_total} />
      </div>

      <Card>
        <h2 className="mb-3 font-semibold">Applications by status</h2>
        <div className="flex flex-wrap gap-2">
          {Object.entries(d.applications_by_status).map(([k, v]) => (
            <span key={k} className="rounded-lg bg-gray-100 px-3 py-1 text-sm">{k}: <b>{v}</b></span>
          ))}
          {Object.keys(d.applications_by_status).length === 0 && <span className="text-sm text-gray-400">None yet.</span>}
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 font-semibold">Scheduled jobs</h2>
        <div className="flex flex-wrap gap-3">
          <Button variant="ghost" disabled={!!job} onClick={() => runJob("scan_all_companies")}>
            {job === "scan_all_companies" ? "Scanning…" : "Run scan-all-companies"}
          </Button>
          <Button variant="ghost" disabled={!!job} onClick={() => runJob("match_all_candidates")}>
            {job === "match_all_candidates" ? "Matching…" : "Run match-all-candidates"}
          </Button>
        </div>
      </Card>
    </div>
  );
}

export default function AdminPage() {
  return (
    <Guard admin>
      <AdminInner />
    </Guard>
  );
}
