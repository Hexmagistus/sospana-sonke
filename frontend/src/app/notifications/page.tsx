"use client";

import { useEffect, useState } from "react";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Alert, Spinner, Button, Badge, EmptyState } from "@/components/ui";
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

  async function markRead(id: string) {
    await api.post(`/notifications/${id}/read`);
    await load();
    window.dispatchEvent(new Event("notifications:changed"));
  }
  async function markAll() {
    await api.post("/notifications/read-all");
    await load();
    window.dispatchEvent(new Event("notifications:changed"));
  }

  if (loading) return <Spinner />;
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
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
        <div className="space-y-2">
          {notes.map((n) => (
            <Card key={n.id} className={n.is_read ? "opacity-60" : ""}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-ss-text">{n.title}</span>
                    <Badge>{n.type}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-ss-muted">{n.body}</p>
                  {n.link_url && (
                    <a
                      href={n.link_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-1 inline-block text-xs font-semibold text-brand hover:underline"
                    >
                      Open →
                    </a>
                  )}
                  <p className="mt-1 text-xs text-ss-muted">{new Date(n.created_at).toLocaleString()}</p>
                </div>
                {!n.is_read && (
                  <button onClick={() => markRead(n.id)} className="text-xs text-brand hover:underline">
                    Mark read
                  </button>
                )}
              </div>
            </Card>
          ))}
        </div>
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
