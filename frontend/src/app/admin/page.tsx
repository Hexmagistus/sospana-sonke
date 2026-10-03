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
  notify_opportunity_alerts?: boolean;
  tagging_email?: boolean | null;
  tags?: string[];
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

interface SourceHealth {
  sources: number;
  employers?: number;
  open_vacancies: number;
  expired_vacancies?: number;
  vacancies_new_today?: number;
  vacancies_new_week?: number;
  duplicates_prevented?: number;
  needs_review?: number;
  last_success_at: string | null;
  by_status: Record<string, number>;
  by_scraper_status?: Record<string, number>;
  by_ats: Record<string, number>;
  recent: {
    source_id?: string | null;
    company_id?: string | null;
    company_name: string;
    country: string | null;
    ats_type: string;
    url: string;
    active?: boolean;
    scraper_status?: string | null;
    last_status: string;
    last_error: string | null;
    last_checked: string | null;
    last_vacancy_count: number | null;
    consecutive_failures: number;
  }[];
}

interface ScanLogRow {
  id: string;
  company_id: string;
  company_name: string | null;
  url: string | null;
  status: string;
  error_category: string | null;
  pages_scanned: number;
  vacancies_discovered: number;
  vacancies_new: number;
  vacancies_updated: number;
  duplicates_prevented: number;
  vacancies_closed: number;
  duration_ms: number | null;
  parser_used: string | null;
  finished_at: string | null;
}

function SourceHealthCard() {
  const [health, setHealth] = useState<SourceHealth | null>(null);
  const [logs, setLogs] = useState<ScanLogRow[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [err, setErr] = useState("");
  const [busyId, setBusyId] = useState("");

  function load(status = statusFilter) {
    api.get<SourceHealth>("/admin/source-health").then(setHealth).catch((e) => setErr(e.message));
    const q = status ? `?status=${encodeURIComponent(status)}` : "";
    api.get<ScanLogRow[]>(`/admin/scan-logs${q}`).then(setLogs).catch((e) => setErr(e.message));
  }
  useEffect(() => { load(""); }, []);

  async function pause(row: SourceHealth["recent"][number], active: boolean) {
    if (!row.source_id) return;
    setBusyId(row.source_id);
    try {
      await api.post(`/admin/sources/${row.source_id}/active`, { active });
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not update this source");
    } finally {
      setBusyId("");
    }
  }

  async function scanNow(row: SourceHealth["recent"][number]) {
    if (!row.company_id) return;
    setBusyId(row.company_id);
    try {
      await api.post(`/companies/${row.company_id}/scan`, {});
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Scan failed");
    } finally {
      setBusyId("");
    }
  }

  return (
    <Card>
      <h2 className="mb-1 font-semibold">Careers-source health</h2>
      <p className="mb-3 text-sm text-ss-muted">
        Each employer is scanned on its own. One failure does not stop the run.
        GitHub Actions asks the API every 15 minutes; GitHub may delay that.
        A public feed with roles is due again after about an hour, an ordinary page after about six hours.
        A board that keeps returning no roles waits 12 hours, then a day, then a week.
        Scan now is limited to 20 times an hour.
      </p>
      {err && <Alert kind="error">{err}</Alert>}
      {!health && !err && <Spinner />}
      {health && (
        <>
          <p className="mb-3 text-sm text-ss-text">
            {health.employers ?? "—"} employers · {health.sources} sources · {health.open_vacancies} open vacancies
            {" · "}{health.vacancies_new_today ?? 0} new today · {health.vacancies_new_week ?? 0} this week
            {" · "}{health.expired_vacancies ?? 0} expired · {health.duplicates_prevented ?? 0} duplicates prevented
            {" · "}{health.needs_review ?? 0} need review · last successful read{" "}
            <strong>{health.last_success_at ? health.last_success_at.slice(0, 16).replace("T", " ") + " UTC" : "not yet"}</strong>
          </p>
          <div className="mb-3 flex flex-wrap gap-2">
            {Object.entries(health.by_scraper_status || {}).map(([k, v]) => (
              <span key={`s-${k}`} className="rounded-lg bg-ss-border px-3 py-1 text-sm text-ss-text">{k}: <b>{v}</b></span>
            ))}
            {Object.entries(health.by_status).map(([k, v]) => (
              <span key={k} className="rounded-lg bg-ss-border px-3 py-1 text-sm text-ss-text">{k}: <b>{v}</b></span>
            ))}
            {Object.entries(health.by_ats).map(([k, v]) => (
              <span key={k} className="rounded-lg border border-ss-border px-3 py-1 text-sm text-ss-muted">{k}: <b className="text-ss-text">{v}</b></span>
            ))}
            {health.sources === 0 && <span className="text-sm text-ss-muted">No sources scanned yet.</span>}
          </div>
          {health.recent.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-ss-muted">
                    <th className="py-2 pr-3">Employer</th>
                    <th className="py-2 pr-3">Feed</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3">Jobs</th>
                    <th className="py-2 pr-3">Checked</th>
                    <th className="py-2 pr-3">Last error</th>
                    <th className="py-2 pr-3"> </th>
                  </tr>
                </thead>
                <tbody>
                  {health.recent.map((row) => (
                    <tr key={row.source_id || row.url} className="border-t border-ss-border">
                      <td className="py-2 pr-3">{row.company_name}</td>
                      <td className="py-2 pr-3">{row.ats_type}</td>
                      <td className="py-2 pr-3">{row.scraper_status || row.last_status}{row.consecutive_failures ? ` · ${row.consecutive_failures} fails` : ""}{row.active === false ? " · paused" : ""}</td>
                      <td className="py-2 pr-3">{row.last_vacancy_count ?? "—"}</td>
                      <td className="py-2 pr-3 text-ss-muted">{row.last_checked ? row.last_checked.slice(0, 16).replace("T", " ") : "—"}</td>
                      <td className="max-w-xs truncate py-2 pr-3 text-ss-muted" title={row.last_error || ""}>{row.last_error || "—"}</td>
                      <td className="py-2 pr-3 whitespace-nowrap">
                        <button type="button" className="mr-2 text-xs font-medium text-ss-text underline" disabled={busyId !== ""} onClick={() => scanNow(row)}>Scan now</button>
                        <button type="button" className="text-xs font-medium text-ss-muted underline" disabled={busyId !== ""} onClick={() => pause(row, row.active === false)}>
                          {row.active === false ? "Resume" : "Pause"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="mt-4">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-semibold text-ss-text">Scan log</h3>
              <label className="text-xs text-ss-muted">
                Status{" "}
                <input value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
                  className="ml-1 rounded border border-ss-border bg-transparent px-2 py-1 text-ss-text" placeholder="ok" />
              </label>
              <button type="button" className="text-xs font-medium text-ss-text underline" onClick={() => load(statusFilter)}>Filter</button>
            </div>
            {logs.length === 0 && <p className="text-sm text-ss-muted">No scan log rows yet.</p>}
            {logs.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-ss-muted">
                      <th className="py-2 pr-3">Employer</th>
                      <th className="py-2 pr-3">Status</th>
                      <th className="py-2 pr-3">Parser</th>
                      <th className="py-2 pr-3">New</th>
                      <th className="py-2 pr-3">Updated</th>
                      <th className="py-2 pr-3">Dupes kept</th>
                      <th className="py-2 pr-3">Closed</th>
                      <th className="py-2 pr-3">ms</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((row) => (
                      <tr key={row.id} className="border-t border-ss-border">
                        <td className="py-2 pr-3">{row.company_name || row.company_id}</td>
                        <td className="py-2 pr-3">{row.status}{row.error_category ? ` · ${row.error_category}` : ""}</td>
                        <td className="py-2 pr-3">{row.parser_used || "—"}</td>
                        <td className="py-2 pr-3">{row.vacancies_new}</td>
                        <td className="py-2 pr-3">{row.vacancies_updated}</td>
                        <td className="py-2 pr-3">{row.duplicates_prevented}</td>
                        <td className="py-2 pr-3">{row.vacancies_closed}</td>
                        <td className="py-2 pr-3 text-ss-muted">{row.duration_ms ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
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
  const [preferenceOnly, setPreferenceOnly] = useState(false);
  const [tagDraft, setTagDraft] = useState<Record<string, string>>({});
  const [prefMail, setPrefMail] = useState<{
    eligible: number; would_send: number; sent: number; sent_today: number;
    daily_cap: number; remaining_today: number; resume_on?: string | null; dry_run: boolean;
  } | null>(null);
  const [prefBusy, setPrefBusy] = useState(false);
  const [prefMsg, setPrefMsg] = useState("");
  const [prefErr, setPrefErr] = useState("");

  function emailChoice(u: AdminUser) {
    if (u.tagging_email === true) return "Yes";
    if (u.tagging_email === false) return "No";
    return "Not chosen";
  }

  async function load() {
    setD(await api.get<AdminDashboard>("/admin/dashboard"));
  }
  function loadUsers(pref: boolean) {
    const q = pref ? "?with_preference=true" : "";
    api.get<AdminUser[]>(`/admin/users${q}`).then(setUsers).catch(() => {});
  }
  useEffect(() => {
    load().catch((e) => setErr(e.message));
    loadUsers(false);
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
      const res = await api.post<{ sent: number; skipped: number; duplicates?: number; emailed?: number }>("/admin/suggestions", {
        title: suggestTitle.trim(),
        body: suggestBody.trim(),
        link_url: suggestLink.trim() || undefined,
        all_candidates: allCandidates,
        user_ids: allCandidates ? [] : Array.from(selected),
      });
      const duplicates = res.duplicates || 0;
      const emailed = res.emailed || 0;
      const parts = allCandidates
        ? [`Sent an in-app notice to ${res.sent} opted-in candidate${res.sent === 1 ? "" : "s"}.`]
        : [`Stored an in-app notice for ${res.sent} candidate${res.sent === 1 ? "" : "s"}.`];
      if (emailed) parts.push(`Emailed ${emailed} who chose tagging email.`);
      if (res.skipped) {
        parts.push(allCandidates
          ? `Skipped ${res.skipped} who have not opted in to a broadcast.`
          : `Skipped ${res.skipped}.`);
      }
      if (duplicates) {
        parts.push(`${duplicates} already had a notice for this link.`);
      }
      setSuggestMsg(parts.join(" "));
      setSuggestTitle(""); setSuggestBody(""); setSuggestLink(""); setSelected(new Set());
    } catch (e) {
      setSuggestErr(e instanceof Error ? e.message : "Failed to send.");
    } finally {
      setSuggestBusy(false);
    }
  }

  async function runPrefMail(dry: boolean) {
    setPrefBusy(true); setPrefErr(""); setPrefMsg("");
    try {
      const res = await api.post<{
        eligible: number; would_send: number; sent: number; sent_today: number;
        daily_cap: number; remaining_today: number; resume_on?: string | null; dry_run: boolean;
      }>("/admin/tagging-preference-email", { dry_run: dry, batch: 40 });
      setPrefMail(res);
      if (dry) {
        setPrefMsg(`${res.eligible} people have no email choice. This batch would send ${res.would_send}. ${res.sent_today} already sent today (cap ${res.daily_cap} a UTC day).`);
      } else {
        const later = res.resume_on ? ` Resume on ${res.resume_on}.` : "";
        setPrefMsg(`Sent ${res.sent}. ${res.eligible} still have no recorded choice.${later}`);
      }
    } catch (e) {
      setPrefErr(e instanceof Error ? e.message : "Could not send that email");
    } finally {
      setPrefBusy(false);
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
          <Button variant="ghost" disabled={!!job} loading={job === "scan_due_companies"} onClick={() => runJob("scan_due_companies")}>
            {job === "scan_due_companies" ? "Scanning the next batch…" : "Scan the next batch"}
          </Button>
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

      <SourceHealthCard />

      <Card>
        <h2 className="mb-1 font-semibold">Suggest a post or link</h2>
        <p className="mb-3 text-sm text-ss-muted">
          A selected person gets an in-app notice with the pasted link, whether or not they chose email.
          The email goes only to people who turned tagging email on. Send to everyone stays limited to
          people who opted in. The same person is not notified twice for the same link. The audit log
          records the counts, not their email address.
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
            Send to everyone who opted in
          </Button>
        </div>
      </Card>

      <Card>
        <h2 className="mb-1 font-semibold">One email about notification settings</h2>
        <p className="mb-3 text-sm text-ss-muted">
          For account holders who have never chosen whether a tag may be emailed. The message names
          Sospana Sonke, explains the in-account notice, and links to the preferences page. It has no
          listings. Count first. Then send one batch of 40. It stops at 300 a UTC day and continues
          the next day. Each address is recorded, so nobody receives it twice.
        </p>
        {prefErr && <Alert kind="error">{prefErr}</Alert>}
        {prefMsg && <Alert kind="success">{prefMsg}</Alert>}
        <div className="mt-3 flex flex-wrap gap-3">
          <Button onClick={() => runPrefMail(true)} disabled={prefBusy} loading={prefBusy && prefMail === null}>
            Count people with no email choice
          </Button>
          <Button
            variant="ghost"
            onClick={() => runPrefMail(false)}
            disabled={prefBusy || !prefMail || prefMail.would_send === 0}
          >
            Send one batch
          </Button>
        </div>
      </Card>

      <Card>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold">Registered users ({users.length})</h2>
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-ss-muted">
              <input
                type="checkbox"
                checked={preferenceOnly}
                onChange={(e) => {
                  setPreferenceOnly(e.target.checked);
                  loadUsers(e.target.checked);
                }}
              />
              Has a preferred post
            </label>
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
                <th className="py-2 pr-4">Tag email</th>
                <th className="py-2 pr-4">Tags</th>
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
                  <td className="py-2 pr-4">
                    <span className="rounded-full bg-ss-border px-2 py-0.5 text-xs font-semibold text-ss-muted">
                      {emailChoice(u)}
                    </span>
                  </td>
                  <td className="py-2 pr-4">
                    <div className="flex flex-col gap-1">
                      <span>{(u.tags || []).join(", ") || "—"}</span>
                      {u.role === "candidate" && u.is_active && (
                        <form
                          className="flex gap-1"
                          onSubmit={async (e) => {
                            e.preventDefault();
                            const tag = (tagDraft[u.id] || "").trim();
                            if (!tag) return;
                            const link = suggestLink.trim();
                            try {
                              const res = await api.post<{
                                tags: string[];
                                notice_sent?: number;
                                notice_duplicate?: number;
                              }>(`/admin/users/${u.id}/tags`, {
                                tag,
                                link_url: link || undefined,
                              });
                              setUsers((prev) => prev.map((row) => row.id === u.id ? { ...row, tags: res.tags } : row));
                              setTagDraft((d) => ({ ...d, [u.id]: "" }));
                              if (link && res.notice_sent) {
                                setSuggestErr("");
                                setSuggestMsg("Tagged. They have a notice with that link.");
                              } else if (link && res.notice_duplicate) {
                                setSuggestErr("");
                                setSuggestMsg("Tagged. They already had a notice for this link.");
                              }
                            } catch (ex) {
                              setSuggestErr(ex instanceof Error ? ex.message : "Could not tag");
                            }
                          }}
                        >
                          <input
                            value={tagDraft[u.id] || ""}
                            onChange={(e) => setTagDraft((d) => ({ ...d, [u.id]: e.target.value }))}
                            placeholder="Tag"
                            maxLength={40}
                            className="w-24 rounded border border-ss-border bg-ss-surface px-2 py-1 text-xs"
                            aria-label={`Tag ${u.email}`}
                          />
                          <button type="submit" className="text-xs font-semibold text-brand">Add</button>
                        </form>
                      )}
                    </div>
                  </td>
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
                <tr><td colSpan={10} className="py-3 text-ss-muted">No users yet. The kettle is on.</td></tr>
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
