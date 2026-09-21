"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, getToken } from "@/lib/api";

type Tip = { id: string; kind: string; body: string | null; author: string; mine: boolean; created_at: string };
type Resp = { counts: Record<string, number>; comments: Tip[] };

const TAGS: { k: string; label: string }[] = [
  { k: "works", label: "✅ Link works" },
  { k: "broken", label: "⚠️ Link broken" },
  { k: "open", label: "🕒 Applications open" },
  { k: "closed", label: "🔒 Closed" },
  { k: "tip", label: "💡 Tip" },
];
const LABEL = Object.fromEntries(TAGS.map((t) => [t.k, t.label]));

/** Short community tips under an employer link, so other job-seekers can decide quickly. */
export function CompanyTips({ companyId }: { companyId: string }) {
  const [authed, setAuthed] = useState(false);
  const [data, setData] = useState<Resp | null>(null);
  const [kind, setKind] = useState("works");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadErr, setLoadErr] = useState(false);
  const [err, setErr] = useState("");
  const [members, setMembers] = useState<{ id: string; name: string; position: string | null }[]>([]);
  const [tagged, setTagged] = useState<{ id: string; name: string }[]>([]);

  useEffect(() => {
    if (!getToken()) return;
    api.get<{ id: string; name: string; position: string | null }[]>("/messages/members")
      .then(setMembers).catch(() => setMembers([]));
  }, []);

  function tag(m: { id: string; name: string }) {
    if (tagged.length >= 3 || tagged.some((t) => t.id === m.id)) return;
    setTagged([...tagged, m]);
    setText((t) => `${t}${t && !t.endsWith(" ") ? " " : ""}@${m.name} `.slice(0, 300));
  }

  const load = useCallback(() => {
    setLoadErr(false);
    api.get<Resp>(`/companies/${companyId}/comments`).then(setData).catch(() => {
      setLoadErr(true);
      window.setTimeout(() => api.get<Resp>(`/companies/${companyId}/comments`).then((d) => { setData(d); setLoadErr(false); }).catch(() => {}), 4000);
    });
  }, [companyId]);

  useEffect(() => {
    setAuthed(!!getToken());
    load();
  }, [load]);

  async function post() {
    setBusy(true);
    setErr("");
    try {
      await api.post(`/companies/${companyId}/comments`, { kind, body: text.trim() || null, mentions: tagged.map((t) => t.id) });
      setText("");
      setTagged([]);
      load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not post.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-5 border-t border-gray-100 pt-4">
      <div className="text-sm font-bold text-navy">💬 Community tips</div>
      <p className="mt-0.5 text-xs text-gray-500">
        Quick notes from other members to help you decide faster. Visible to everyone; tips are kept for 30 days.
      </p>
      {(<>
          {data && data.comments.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5 text-[11px] text-gray-600">
              {TAGS.filter((t) => t.k !== "tip" && (data.counts[t.k] || 0) > 0).map((t) => (
                <span key={t.k} className="rounded-full bg-gray-100 px-2 py-0.5">{t.label} · {data.counts[t.k]}</span>
              ))}
            </div>
          )}
          {loadErr && !data && <p className="mt-2 text-xs text-amber-600">Loading tips… the server may be waking up, retrying.</p>}
          <ul className="mt-2 space-y-2">
            {data?.comments.length === 0 && <li className="text-xs text-gray-400">No tips yet. Be the first to help others.</li>}
            {data?.comments.map((c) => (
              <li key={c.id} className="rounded-lg bg-gray-50 px-3 py-2 text-xs text-gray-700">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold">{LABEL[c.kind]}</span>
                  <span className="text-[10px] text-gray-400">{c.author} · {new Date(c.created_at).toLocaleDateString()}</span>
                </div>
                {c.body && <p className="mt-1 break-words">{c.body}</p>}
                <div className="mt-1 text-right text-[10px]">
                  {!authed ? null : c.mine ? (
                    <button className="text-gray-400 hover:text-red-600" onClick={() => api.del(`/comments/${c.id}`).then(load)}>Delete</button>
                  ) : (
                    <button className="text-gray-400 hover:text-red-600" onClick={() => api.post(`/comments/${c.id}/flag`).then(load)}>Report</button>
                  )}
                </div>
              </li>
            ))}
          </ul>
          {!authed ? (
            <p className="mt-3 text-xs text-gray-600">
              <Link href="/login" className="font-semibold text-brand-dark underline">Sign in</Link> to add a tip.
            </p>
          ) : (<>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {TAGS.map((t) => (
              <button key={t.k} onClick={() => setKind(t.k)}
                className={`rounded-full border px-2.5 py-1 text-[11px] ${kind === t.k ? "border-brand-dark bg-brand-dark text-white" : "border-gray-200 text-gray-600"}`}>
                {t.label}
              </button>
            ))}
          </div>
          <textarea value={text} onChange={(e) => setText(e.target.value)} maxLength={300} rows={2}
            placeholder={kind === "tip" ? "Your tip (no links, emails or phone numbers)" : "Optional short note"}
            className="mt-2 w-full rounded-lg border border-gray-300 bg-white p-2 text-xs text-black placeholder:text-gray-500" />
          <div className="mt-2">
            <select value="" onChange={(e) => { const m = members.find((x) => x.id === e.target.value); if (m) tag(m); }}
              className="w-full rounded-lg border border-gray-300 bg-white p-2 text-xs text-black">
              <option value="">{members.length ? "@ Tag a member…" : "No members available to tag yet"}</option>
              {members.filter((m) => !tagged.some((t) => t.id === m.id)).map((m) => (
                <option key={m.id} value={m.id}>{m.name} — {m.position || "no position set"}</option>
              ))}
            </select>
            {tagged.length > 0 && (
              <div className="mt-1 flex flex-wrap gap-1">
                {tagged.map((t) => (
                  <span key={t.id} className="rounded-full bg-brand/10 px-2 py-0.5 text-[11px] text-brand-dark">
                    @{t.name} <button type="button" aria-label="Remove tag" onClick={() => setTagged(tagged.filter((x) => x.id !== t.id))}>✕</button>
                  </span>
                ))}
              </div>
            )}
            <p className="mt-1 text-[10px] text-gray-400">Only members who allow messages can be tagged (their name and desired position show here). They get a notification.</p>
          </div>
          {err && <p className="mt-1 text-xs text-red-600">{err}</p>}
          <button disabled={busy || (kind === "tip" && !text.trim())} onClick={post}
            className="mt-2 rounded-lg bg-navy px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40">
            {busy ? "Posting…" : "Post tip"}
          </button>
          </>)}
        </>
      )}
    </div>
  );
}
