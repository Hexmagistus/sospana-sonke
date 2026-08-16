"use client";

import { useEffect, useState } from "react";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Alert, Spinner, Button, Badge } from "@/components/ui";
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
  }
  async function markAll() {
    await api.post("/notifications/read-all");
    await load();
  }

  if (loading) return <Spinner />;
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Notifications</h1>
        <Button variant="ghost" onClick={markAll}>Mark all read</Button>
      </div>
      {err && <Alert kind="error">{err}</Alert>}
      {notes.length === 0 ? (
        <Card><p className="text-sm text-gray-500">No notifications yet.</p></Card>
      ) : (
        <div className="space-y-2">
          {notes.map((n) => (
            <Card key={n.id} className={n.is_read ? "opacity-60" : ""}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{n.title}</span>
                    <Badge>{n.type}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-gray-600">{n.body}</p>
                  <p className="mt-1 text-xs text-gray-400">{new Date(n.created_at).toLocaleString()}</p>
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
