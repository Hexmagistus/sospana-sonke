"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Stat, Card, Alert, Spinner, Button } from "@/components/ui";
import type { AdminDashboard } from "@/lib/types";

interface AdminUser {
  id: string;
  email: string;
  name: string;
  mobile_number: string | null;
  role: string;
  email_verified: boolean;
  is_active: boolean;
  created_at: string | null;
  has_profile: boolean;
  city: string | null;
  current_occupation: string | null;
}

function AdminInner() {
  const [d, setD] = useState<AdminDashboard | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [err, setErr] = useState("");
  const [job, setJob] = useState("");
  const [copied, setCopied] = useState(false);

  async function load() {
    setD(await api.get<AdminDashboard>("/admin/dashboard"));
  }
  useEffect(() => {
    load().catch((e) => setErr(e.message));
    api.get<AdminUser[]>("/admin/users").then(setUsers).catch(() => {});
  }, []);

  function copyEmails() {
    const list = users.map((u) => u.email).join(", ");
    navigator.clipboard?.writeText(list);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

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
          <Button variant="ghost" disabled={!!job} onClick={() => runJob("scan_south_africa")}>
            {job === "scan_south_africa" ? "Scanning South Africa…" : "Scan South Africa now"}
          </Button>
          <Button variant="ghost" disabled={!!job} onClick={() => runJob("scan_all_companies")}>
            {job === "scan_all_companies" ? "Scanning…" : "Run scan-all-companies (all regions)"}
          </Button>
          <Button variant="ghost" disabled={!!job} onClick={() => runJob("match_all_candidates")}>
            {job === "match_all_candidates" ? "Matching…" : "Run match-all-candidates"}
          </Button>
        </div>
      </Card>

      <Card>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold">Registered users ({users.length})</h2>
          <Button variant="ghost" onClick={copyEmails} disabled={users.length === 0}>
            {copied ? "Copied!" : "Copy all emails"}
          </Button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500">
                <th className="py-2 pr-4">Email</th>
                <th className="py-2 pr-4">Name</th>
                <th className="py-2 pr-4">Mobile</th>
                <th className="py-2 pr-4">Profile</th>
                <th className="py-2 pr-4">Joined</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t border-gray-100">
                  <td className="py-2 pr-4 font-medium text-navy">{u.email}</td>
                  <td className="py-2 pr-4">{u.name}</td>
                  <td className="py-2 pr-4">{u.mobile_number || "—"}</td>
                  <td className="py-2 pr-4">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${u.has_profile ? "bg-brand/10 text-brand-dark" : "bg-gray-100 text-gray-500"}`}>
                      {u.has_profile ? "Yes" : "No"}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-gray-500">{u.created_at ? u.created_at.slice(0, 10) : "—"}</td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr><td colSpan={5} className="py-3 text-gray-400">No users yet.</td></tr>
              )}
            </tbody>
          </table>
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
