"use client";

import { useEffect, useState } from "react";
import Guard from "@/components/Guard";
import NoticeLink from "@/components/NoticeLink";
import { api } from "@/lib/api";
import { Alert, Spinner, Button, Badge, EmptyState } from "@/components/ui";
import type { Notification } from "@/lib/types";

function NotificationsInner() {
  const [notes, setNotes] = useState<Notification[]>([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setNotes(await api.get<Notification[]>("/notifications"));
    setLoading(false);
  }
  useEffect(() => {
    load().catch((e) => { setErr(e.message); setLoading(false); });
  }, []);

  useEffect(() => {
    function refresh() { load().catch((e) => setErr(e.message)); }
    window.addEventListener("notifications:changed", refresh);
    return () => window.removeEventListener("notifications:changed", refresh);
  }, []);

  async function markAll() {
    await api.post("/notifications/read-all");
    await load();
    window.dispatchEvent(new Event("notifications:changed"));
  }

  if (loading) return <Spinner />;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-ss-text">Notifications</h1>
        <Button variant="ghost" onClick={markAll}>Mark all read</Button>
      </div>
      {err && <Alert kind="error">{err}</Alert>}
      {notes.length === 0 ? (
        <EmptyState
          icon="🔔"
          title="No notifications yet"
          message="You'll see updates here as your Career Agent finds matches, prepares applications and hears back from employers."
        />
      ) : (
        <ul className="space-y-2">
          {notes.map((n) => (
            <li key={n.id}>
              <NoticeLink note={n} className={n.is_read ? "opacity-60" : ""}>
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-ss-text">{n.title}</span>
                  <Badge>{n.type}</Badge>
                  {!n.is_read && <span className="text-[11px] font-semibold uppercase tracking-wide text-ss-primary">Unread</span>}
                </span>
                <span className="mt-1 block whitespace-pre-wrap break-words text-sm text-ss-muted">{n.body}</span>
                {n.type === "admin_suggestion" && (
                  <span className="mt-2 block text-xs font-semibold text-ss-text">Tagged by the Sospana Sonke team</span>
                )}
                <span className="mt-1 block text-xs text-ss-muted">
                  {n.type === "admin_suggestion" ? "Tagged " : ""}
                  {new Date(n.created_at).toLocaleString()}
                </span>
              </NoticeLink>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function NotificationsPage() {
  return (
    <Guard>
      <NotificationsInner />
    </Guard>
  );
}
