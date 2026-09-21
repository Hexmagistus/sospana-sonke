"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Card, Alert, Spinner, Button, Input, Textarea, EmptyState } from "@/components/ui";

interface Msg {
  id: string; other_user_id: string; other_name: string; body: string;
  direction: "in" | "out"; created_at: string; expires_at: string; read: boolean;
}
interface Person { id: string; name: string }
interface Settings { allow_messages: boolean; messaging_banned: boolean; ttl_hours: number }

const REASONS: [string, string][] = [
  ["harassment", "Harassment or threats"], ["scam", "Scam or asking for money"],
  ["spam", "Spam"], ["inappropriate", "Inappropriate content"], ["other", "Something else"],
];

function timeLeft(iso: string): string {
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return "expiring";
  const h = Math.floor(ms / 3.6e6), m = Math.floor((ms % 3.6e6) / 6e4);
  return h > 0 ? `${h}h ${m}m left` : `${m}m left`;
}

function MessagesInner() {
  const { refreshUser } = useAuth();
  const [tab, setTab] = useState<"inbox" | "sent" | "new" | "blocked">("inbox");
  const [settings, setSettings] = useState<Settings | null>(null);
  const [inbox, setInbox] = useState<Msg[]>([]);
  const [sent, setSent] = useState<Msg[]>([]);
  const [blocks, setBlocks] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");

  const [q, setQ] = useState("");
  const [results, setResults] = useState<Person[] | null>(null);
  const [to, setTo] = useState<Person | null>(null);
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [reporting, setReporting] = useState<Msg | null>(null);
  const [reason, setReason] = useState("harassment");
  const [note, setNote] = useState("");

  const load = useCallback(async () => {
    const [s, i, o, b] = await Promise.all([
      api.get<Settings>("/messages/settings"),
      api.get<Msg[]>("/messages/inbox"),
      api.get<Msg[]>("/messages/sent"),
      api.get<Person[]>("/messages/blocks"),
    ]);
    setSettings(s); setInbox(i); setSent(o); setBlocks(b); setLoading(false);
    window.dispatchEvent(new Event("messages:changed"));
  }, []);
  useEffect(() => { load().catch((e) => { setErr(e.message); setLoading(false); }); }, [load]);

  function fail(e: unknown) { setOk(""); setErr(e instanceof Error ? e.message : "Something went wrong"); }
  function good(m: string) { setErr(""); setOk(m); }

  async function toggleOptIn(v: boolean) {
    try { await api.put("/messages/settings", { allow_messages: v }); await load(); await refreshUser(); good(v ? "Others can now message you. Messages vanish after 24 hours." : "Messaging switched off. Nobody can message you."); }
    catch (e) { fail(e); }
  }
  async function search() {
    setResults(null);
    try { setResults(await api.get<Person[]>(`/messages/directory?q=${encodeURIComponent(q.trim())}`)); }
    catch (e) { fail(e); }
  }
  async function send() {
    if (!to) return;
    setBusy(true);
    try {
      await api.post("/messages", { recipient_id: to.id, body });
      setBody(""); setTo(null); setResults(null); setQ("");
      await load(); setTab("sent"); good("Sent. It will be deleted automatically in 24 hours.");
    } catch (e) { fail(e); } finally { setBusy(false); }
  }
  async function markRead(m: Msg) {
    if (m.direction === "in" && !m.read) { await api.post(`/messages/${m.id}/read`).catch(() => {}); await load(); }
  }
  async function remove(m: Msg) {
    try { await api.del(`/messages/${m.id}`); await load(); } catch (e) { fail(e); }
  }
  async function block(id: string) {
    try { await api.post(`/messages/blocks/${id}`); await load(); good("Blocked. They can no longer message you."); } catch (e) { fail(e); }
  }
  async function unblock(id: string) {
    try { await api.del(`/messages/blocks/${id}`); await load(); } catch (e) { fail(e); }
  }
  async function submitReport() {
    if (!reporting) return;
    try {
      await api.post(`/messages/${reporting.id}/report`, { reason, note: note || null });
      setReporting(null); setNote(""); await load();
      good("Reported and blocked. An administrator will review it. Thank you for keeping the community safe.");
    } catch (e) { fail(e); }
  }

  if (loading) return <Spinner />;

  const list = tab === "inbox" ? inbox : sent;
  const tabBtn = (t: typeof tab, label: string) => (
    <button key={t} onClick={() => setTab(t)}
      className={`rounded-md px-3 py-1.5 text-sm transition ${tab === t ? "bg-gradient-to-r from-brand to-brand-dark text-white shadow-sm" : "bg-ss-border text-ss-muted hover:bg-ss-primary-soft hover:text-ss-text"}`}>
      {label}
    </button>
  );

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-ss-text">Messages</h1>
        <p className="ss-hud-tag mt-1 text-[11px] text-ss-muted">⏳ Temporary by design: every message is deleted 24 hours after it is sent</p>
      </div>
      {err && <Alert kind="error">{err}</Alert>}
      {ok && <Alert kind="success">{ok}</Alert>}

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="font-semibold text-ss-text">Let others message me</div>
            <p className="text-sm text-ss-muted">
              Off by default. When on, other members can find you by first name and last initial only. Your email and phone are never shown.
            </p>
          </div>
          <label className="flex cursor-pointer items-center gap-2 text-sm font-semibold text-ss-text">
            <input type="checkbox" checked={!!settings?.allow_messages} onChange={(e) => toggleOptIn(e.target.checked)} />
            {settings?.allow_messages ? "On" : "Off"}
          </label>
        </div>
        {settings?.messaging_banned && (
          <div className="mt-3"><Alert kind="error">Your ability to send messages has been suspended after a report. Contact the Information Officer if you think this is a mistake.</Alert></div>
        )}
      </Card>

      <Card>
        <p className="text-sm text-ss-muted">
          <strong className="text-ss-text">Stay safe.</strong> Messages are monitored for abuse and scams. Links, email addresses,
          phone numbers and requests for money are blocked. Never pay anyone to get a job. Use Report on anything that feels wrong;
          a reported message is kept for an administrator to review for up to 30 days, then deleted. See our{" "}
          <Link href="/privacy" className="text-brand hover:underline">Privacy Policy</Link>.
        </p>
      </Card>

      <div className="flex flex-wrap gap-1">
        {tabBtn("inbox", `Inbox (${inbox.length})`)}
        {tabBtn("sent", `Sent (${sent.length})`)}
        {tabBtn("new", "✉️ New message")}
        {tabBtn("blocked", `Blocked (${blocks.length})`)}
      </div>

      {(tab === "inbox" || tab === "sent") && (
        list.length === 0 ? (
          <EmptyState icon="💬" title={tab === "inbox" ? "No messages" : "Nothing sent"}
            message={tab === "inbox" ? "Messages you receive appear here for 24 hours." : "Messages you send appear here for 24 hours."} />
        ) : (
          <div className="space-y-3">
            {list.map((m) => (
              <div key={m.id} onClick={() => markRead(m)}
                className={`ss-hud-card rounded-2xl border bg-ss-surface p-4 ${m.direction === "in" && !m.read ? "border-gold" : "border-ss-border"}`}>
                <span aria-hidden className="ss-hud-scan" />
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-semibold text-ss-text">
                    {m.direction === "in" ? "From" : "To"} {m.other_name}
                    {m.direction === "in" && !m.read && <span className="ml-2 rounded-full bg-gold px-2 py-0.5 text-[10px] font-bold text-navy">NEW</span>}
                  </div>
                  <span className="ss-hud-tag text-[11px] text-ss-muted">⏳ {timeLeft(m.expires_at)}</span>
                </div>
                <p className="mt-2 whitespace-pre-wrap break-words text-sm text-ss-text">{m.body}</p>
                <div className="mt-3 flex flex-wrap gap-2 text-xs" onClick={(e) => e.stopPropagation()}>
                  <button className="text-ss-muted hover:text-ss-text hover:underline" onClick={() => remove(m)}>Delete now</button>
                  {m.direction === "in" && (
                    <>
                      <button className="text-ss-muted hover:text-ss-text hover:underline" onClick={() => setReporting(m)}>🚩 Report</button>
                      <button className="text-ss-muted hover:text-ss-text hover:underline" onClick={() => block(m.other_user_id)}>Block</button>
                      <button className="font-semibold text-brand-dark hover:underline"
                        onClick={() => { setTo({ id: m.other_user_id, name: m.other_name }); setTab("new"); }}>Reply</button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {tab === "new" && (
        <Card>
          <div className="space-y-3">
            {!to ? (
              <>
                <p className="text-sm text-ss-muted">Find a member (only people who switched messaging on appear).</p>
                <div className="flex gap-2">
                  <div className="flex-1"><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by first or last name (min 2 letters)"
                    onKeyDown={(e) => { if (e.key === "Enter" && q.trim().length >= 2) search(); }} /></div>
                  <Button onClick={search} disabled={q.trim().length < 2}>Search</Button>
                </div>
                {results && results.length === 0 && <p className="text-sm text-ss-muted">No members found. They may not have switched messaging on.</p>}
                {results && results.map((p) => (
                  <button key={p.id} onClick={() => setTo(p)}
                    className="block w-full rounded-lg border border-ss-border px-3 py-2 text-left text-sm hover:border-brand hover:bg-ss-primary-soft">{p.name}</button>
                ))}
              </>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-ss-text">To: {to.name}</div>
                  <button className="text-xs text-ss-muted hover:underline" onClick={() => setTo(null)}>Change</button>
                </div>
                <Textarea rows={4} maxLength={500} value={body} onChange={(e) => setBody(e.target.value)} placeholder="Write a short message…" />
                <div className="flex items-center justify-between">
                  <span className="ss-hud-tag text-[11px] text-ss-muted">{body.length}/500 · deleted after 24h</span>
                  <Button onClick={send} disabled={busy || !body.trim() || !!settings?.messaging_banned} loading={busy}>Send</Button>
                </div>
              </>
            )}
          </div>
        </Card>
      )}

      {tab === "blocked" && (
        blocks.length === 0 ? <EmptyState icon="🛡️" title="No blocked members" message="People you block or report appear here." /> : (
          <Card>
            <div className="space-y-2">
              {blocks.map((p) => (
                <div key={p.id} className="flex items-center justify-between text-sm">
                  <span className="text-ss-text">{p.name}</span>
                  <button className="text-brand-dark hover:underline" onClick={() => unblock(p.id)}>Unblock</button>
                </div>
              ))}
            </div>
          </Card>
        )
      )}

      {reporting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md space-y-3 rounded-2xl border border-ss-border bg-ss-surface p-5 shadow-xl">
            <h2 className="text-lg font-semibold text-ss-text">Report this message</h2>
            <p className="text-sm text-ss-muted">The sender will also be blocked. An administrator keeps a copy of the message for up to 30 days to review it.</p>
            <select value={reason} onChange={(e) => setReason(e.target.value)}
              className="w-full rounded-lg border border-ss-border bg-ss-surface px-3 py-2 text-sm text-ss-text">
              {REASONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <Textarea rows={2} maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Anything we should know? (optional)" />
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setReporting(null)}>Cancel</Button>
              <Button variant="danger" onClick={submitReport}>Report and block</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function MessagesPage() {
  return (
    <Guard>
      <MessagesInner />
    </Guard>
  );
}
