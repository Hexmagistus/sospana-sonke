"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Alert, Button, Card } from "@/components/ui";

type MailResult = {
  dry_run: boolean;
  eligible: number;
  skipped_no_email: number;
  already_sent: number;
  sent_last_24h: number;
  remaining_today: number;
  daily_cap: number;
  provider_daily_limit: number;
  would_send: number;
  sent: number;
  failed: number;
  resume_at?: string | null;
};

/** Admin-only. Count first, then send one batch at a time. */
export function PreferenceEmailCard() {
  const [res, setRes] = useState<MailResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  async function run(dry: boolean) {
    setBusy(true); setErr(""); setMsg("");
    try {
      const r = await api.post<MailResult>("/admin/preference-email", { dry_run: dry, batch: 40 });
      setRes(r);
      const resume = r.resume_at ? ` More can go after ${new Date(r.resume_at).toLocaleString()}.` : "";
      if (dry) {
        setMsg(
          `${r.eligible} existing users have not chosen all three preferences and have an email address ` +
          `(${r.skipped_no_email} skipped for no email). This batch would send ${r.would_send}. ` +
          `${r.sent_last_24h} emails in the last 24 hours; our cap is ${r.daily_cap} (Brevo free limit ${r.provider_daily_limit}).${resume}`,
        );
      } else {
        setMsg(
          `Sent ${r.sent}${r.failed ? `, ${r.failed} not sent and left for later` : ""}. ` +
          `${r.eligible} still to email.${resume}`,
        );
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not run that");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <h2 className="mb-1 font-semibold">One-time email: choose your preferences</h2>
      <p className="mb-3 text-sm text-ss-muted">
        A short service notice to existing users who have not chosen all three preferences. It contains no job
        content, only a link to the preferences page, why they are getting it (POPIA), and how to opt out. Count
        first, then send one batch of up to 40. It never goes to the same person twice, skips anyone without an
        email address, and stops at {res?.daily_cap ?? 250} in any 24 hours (Brevo free is 300 a day, shared with
        other mail). Come back later and press send again to carry on.
      </p>
      {err && <Alert kind="error">{err}</Alert>}
      {msg && <Alert kind="success">{msg}</Alert>}
      <div className="admin-scroll mt-3">
        <div className="flex w-max min-w-full flex-nowrap gap-3">
          <Button onClick={() => run(true)} disabled={busy} loading={busy && res === null}>
            Count who would get it
          </Button>
          <Button variant="ghost" onClick={() => run(false)} disabled={busy || !res || res.would_send === 0}>
            Send next batch
          </Button>
        </div>
      </div>
    </Card>
  );
}

/** Each admin's own switch. Off unless they turn it on. */
export function LoginAlertsCard() {
  const [on, setOn] = useState<boolean | null>(null);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get<{ email_digest: boolean }>("/admin/login-alerts")
      .then((r) => setOn(r.email_digest))
      .catch((e: Error) => setErr(e.message));
  }, []);

  async function change(next: boolean) {
    setErr(""); setMsg("");
    try {
      const r = await api.put<{ email_digest: boolean }>("/admin/login-alerts", { email_digest: next });
      setOn(r.email_digest);
      setMsg(r.email_digest ? "Daily email digest is on." : "Daily email digest is off.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not save that");
    }
  }

  return (
    <Card>
      <h2 className="mb-1 font-semibold">Client sign-in alerts</h2>
      <p className="mb-3 text-sm text-ss-muted">
        When a client signs in you get a notice in the bell, and it opens this page. Clients are not told, and no
        email goes out for each sign-in. You can also get one short email a day listing who signed in. That is off
        unless you switch it on.
      </p>
      {err && <Alert kind="error">{err}</Alert>}
      {msg && <Alert kind="success">{msg}</Alert>}
      <label className="mt-2 flex min-h-11 items-center gap-2 text-sm text-ss-text">
        <input
          className="shrink-0"
          type="checkbox"
          checked={!!on}
          disabled={on === null}
          onChange={(e) => change(e.target.checked)}
        />
        <span>Email me a daily digest of client sign-ins</span>
      </label>
    </Card>
  );
}
