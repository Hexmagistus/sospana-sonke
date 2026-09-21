"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Stat, Card, Alert, Spinner, Button, Field, Input, Textarea } from "@/components/ui";
import type { AdminDashboard } from "@/lib/types";

interface AdminUser {
  id: string;
  email: string;
  name: string;
  mobile_number: string | null;
  preferred_position: string | null;
  qualification_name: string | null;
  role: string;
  email_verified: boolean;
  is_active: boolean;
  created_at: string | null;
  has_profile: boolean;
  city: string | null;
  current_occupation: string | null;
}

interface MsgReport {
  id: string; sender_id: string; sender_name: string; sender_banned: boolean; reason: string;
  note: string | null; body_snapshot: string; status: string; created_at: string; purge_after: string;
}

function MessageReports() {
  const [rows, setRows] = useState<MsgReport[]>([]);
  const [err, setErr] = useState("");
  const load = () => api.get<MsgReport[]>("/admin/message-reports").then(setRows).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);
  async function resolve(id: string, action: "dismiss" | "suspend_sender") {
    try { await api.post(`/admin/message-reports/${id}/resolve`, { action }); await load(); }
    catch (e) { setErr(e instanceof Error ? e.message : "Failed"); }
  }
  return (
    <Card>
      <h2 className="mb-1 text-lg font-semibold text-ss-text">Reported messages</h2>
      <p className="mb-3 text-sm text-ss-muted">Copies are kept for 30 days for review and then deleted automatically.</p>
      {err && <Alert kind="error">{err}</Alert>}
      {rows.length === 0 && <p className="text-sm text-ss-muted">No reports.</p>}
      <div className="space-y-3">
        {rows.map((r) => (
          <div key={r.id} className="rounded-xl border border-ss-border p-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-semibold text-ss-text">{r.sender_name} · {r.reason}</span>
              <span className="text-xs text-ss-muted">{r.status}{r.sender_banned ? " · sender suspended" : ""} · purges {r.purge_after.slice(0, 10)}</span>
            </div>
            <p className="mt-2 whitespace-pre-wrap break-words text-ss-text">{r.body_snapshot}</p>
            {r.note && <p className="mt-1 text-xs text-ss-muted">Reporter note: {r.note}</p>}
            {r.status === "open" && (
              <div className="mt-2 flex gap-2">
                <Button variant="danger" onClick={() => resolve(r.id, "suspend_sender")}>Suspend sender&apos;s messaging</Button>
                <Button variant="ghost" onClick={() => resolve(r.id, "dismiss")}>Dismiss</Button>
              </div>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}

function AdminInner() {
  const [d, setD] = useState<AdminDashboard | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [err, setErr] = useState("");
  const [job, setJob] = useState("");
  const [copied, setCopied] = useState(false);

  // ---- suggest a post/link to relevant candidates ----
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [suggestTitle, setSuggestTitle] = useState("");
  const [suggestBody, setSuggestBody] = useState("");
  const [suggestLink, setSuggestLink] = useState("");
  const [suggestBusy, setSuggestBusy] = useState(false);
  const [suggestMsg, setSuggestMsg] = useState("");
  const [suggestErr, setSuggestErr] = useState("");

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

  function toggleUser(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected((prev) => (prev.size === users.length ? new Set() : new Set(users.map((u) => u.id))));
  }

  async function sendSuggestion(allCandidates: boolean) {
    setSuggestErr(""); setSuggestMsg("");
    if (!suggestTitle.trim() || !suggestBody.trim()) {
      setSuggestErr("Add a title and a message first.");
      return;
    }
    if (!allCandidates && selected.size === 0) {
      setSuggestErr("Select at least one candidate, or send to everyone instead.");
      return;
    }
    setSuggestBusy(true);
    try {
      const res = await api.post<{ sent: number }>("/admin/suggestions", {
        title: suggestTitle.trim(),
        body: suggestBody.trim(),
        link_url: suggestLink.trim() || undefined,
        all_candidates: allCandidates,
        user_ids: allCandidates ? [] : Array.from(selected),
      });
      setSuggestMsg(`Sent to ${res.sent} candidate${res.sent === 1 ? "" : "s"}.`);
      setSuggestTitle(""); setSuggestBody(""); setSuggestLink(""); setSelected(new Set());
    } catch (e) {
      setSuggestErr(e instanceof Error ? e.message : "Failed to send.");
    } finally {
      setSuggestBusy(false);
    }
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
        <h1 className="text-2xl font-bold text-ss-text">Admin dashboard</h1>
        <Link href="/admin/companies"><Button variant="ghost">Manage companies</Button></Link>
      </div>
      {err && <Alert kind="error">{err}</Alert>}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        <Stat label="Registered candidates" value={d.registered_candidates} />
        <Stat label="Companies" value={d.companies_total} hint={`${d.companies_active} active`} />
        <Stat label="Open vacancies" value={d.vacancies_open} hint={`${d.vacancies_total} total`} />
      </div>

      <Card>
        <h2 className="mb-3 font-semibold">Applications by status</h2>
        <div className="flex flex-wrap gap-2">
          {Object.entries(d.applications_by_status).map(([k, v]) => (
            <span key={k} className="rounded-lg bg-ss-border px-3 py-1 text-sm text-ss-text">{k}: <b>{v}</b></span>
          ))}
          {Object.keys(d.applications_by_status).length === 0 && <span className="text-sm text-ss-muted">None yet.</span>}
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 font-semibold">Scheduled jobs</h2>
        <div className="flex flex-wrap gap-3">
          <Button variant="ghost" disabled={!!job} loading={job === "scan_south_africa"} onClick={() => runJob("scan_south_africa")}>
            {job === "scan_south_africa" ? "Scanning South Africa…" : "Scan South Africa now"}
          </Button>
          <Button variant="ghost" disabled={!!job} loading={job === "scan_all_companies"} onClick={() => runJob("scan_all_companies")}>
            {job === "scan_all_companies" ? "Scanning…" : "Run scan-all-companies (all regions)"}
          </Button>
          <Button variant="ghost" disabled={!!job} loading={job === "match_all_candidates"} onClick={() => runJob("match_all_candidates")}>
            {job === "match_all_candidates" ? "Matching…" : "Run match-all-candidates"}
          </Button>
        </div>
      </Card>

      <Card>
        <h2 className="mb-1 font-semibold">Suggest a post or link</h2>
        <p className="mb-3 text-sm text-ss-muted">
          Curate something relevant -- an article, a resource, a company post -- and alert specific
          candidates (or everyone) with it. It shows up as a notification on their own dashboard/notifications page.
        </p>
        {suggestErr && <Alert kind="error">{suggestErr}</Alert>}
        {suggestMsg && <Alert kind="success">{suggestMsg}</Alert>}
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <Field label="Title">
            <Input value={suggestTitle} onChange={(e) => setSuggestTitle(e.target.value)}
                  placeholder="e.g. New logistics roles opening in Gauteng" maxLength={200} />
          </Field>
          <Field label="Link (optional)" hint="must start with http(s)://">
            <Input value={suggestLink} onChange={(e) => setSuggestLink(e.target.value)}
                  placeholder="https://example.com/article" type="url" />
          </Field>
        </div>
        <Field label="Message" hint={`${suggestBody.length}/2000`}>
          <Textarea value={suggestBody} onChange={(e) => setSuggestBody(e.target.value)}
                    placeholder="Why this is relevant to them" rows={3} maxLength={2000} />
        </Field>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Button onClick={() => sendSuggestion(false)} disabled={suggestBusy} loading={suggestBusy}>
            Send to selected ({selected.size})
          </Button>
          <Button variant="ghost" onClick={() => sendSuggestion(true)} disabled={suggestBusy}>
            Send to all candidates ({users.length})
          </Button>
        </div>
      </Card>

      <Card>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold">Registered users ({users.length})</h2>
          <div className="flex flex-wrap gap-2">
            <Button variant="ghost" onClick={toggleAll} disabled={users.length === 0}>
              {selected.size === users.length && users.length > 0 ? "Deselect all" : "Select all"}
            </Button>
            <Button variant="ghost" onClick={copyEmails} disabled={users.length === 0}>
              {copied ? "Copied!" : "Copy all emails"}
            </Button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-ss-muted">
                <th className="py-2 pr-4">
                  <span className="sr-only">Select</span>
                </th>
                <th className="py-2 pr-4">Email</th>
                <th className="py-2 pr-4">Name</th>
                <th className="py-2 pr-4">Mobile</th>
                <th className="py-2 pr-4">Preferred post</th>
                <th className="py-2 pr-4">Qualification</th>
                <th className="py-2 pr-4">Profile</th>
                <th className="py-2 pr-4">Joined</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t border-ss-border hover:bg-ss-primary-soft">
                  <td className="py-2 pr-4">
                    <input type="checkbox" checked={selected.has(u.id)} onChange={() => toggleUser(u.id)}
                          aria-label={`Select ${u.email}`} />
                  </td>
                  <td className="py-2 pr-4 font-medium text-ss-tech">{u.email}</td>
                  <td className="py-2 pr-4">{u.name}</td>
                  <td className="py-2 pr-4">{u.mobile_number || "—"}</td>
                  <td className="py-2 pr-4">{u.preferred_position || "—"}</td>
                  <td className="py-2 pr-4">{u.qualification_name || "—"}</td>
                  <td className="py-2 pr-4">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${u.has_profile ? "bg-brand/10 text-brand-dark" : "bg-ss-border text-ss-muted"}`}>
                      {u.has_profile ? "Yes" : "No"}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-ss-muted">{u.created_at ? u.created_at.slice(0, 10) : "—"}</td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr><td colSpan={8} className="py-3 text-ss-muted">No users yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <MessageReports />
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
