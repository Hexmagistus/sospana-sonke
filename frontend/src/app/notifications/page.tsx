"use client";

import { useEffect, useState } from "react";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Alert, Spinner, Button, Badge, EmptyState } from "@/components/ui";
import type { Notification } from "@/lib/types";

function listingHref(url: string | null): { href: string; external: boolean } | null {
  if (!url) return null;
  const trimmed = url.trim();
  if (trimmed.startsWith("/") && !trimmed.startsWith("//") && !trimmed.toLowerCase().includes("javascript:")) {
    return { href: trimmed, external: false };
  }
  try {
    const parsed = new URL(trimmed);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return null;
    if (parsed.username || parsed.password) return null;
    return { href: trimmed, external: true };
  } catch {
    return null;
  }
}

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
          {notes.map((n) => {
            const listing = listingHref(n.link_url);
            return (
            <Card key={n.id} className={n.is_read ? "opacity-60" : ""}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-ss-text">{n.title}</span>
                    <Badge>{n.type}</Badge>
                  </div>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-ss-muted">{n.body}</p>
                  {n.type === "admin_suggestion" && (
                    <p className="mt-2 text-xs font-semibold text-ss-text">Tagged by the Sospana Sonke team</p>
                  )}
                  <p className="mt-1 text-xs text-ss-muted">
                    {n.type === "admin_suggestion" ? "Tagged " : ""}
                    {new Date(n.created_at).toLocaleString()}
                  </p>
                  {listing && (
                    <a
                      href={listing.href}
                      target={listing.external ? "_blank" : undefined}
                      rel={listing.external ? "noopener noreferrer" : undefined}
                      className="mt-3 inline-block rounded-lg bg-gradient-to-br from-[#163e73] to-[#0b1f3a] px-4 py-2 text-sm font-semibold text-white ring-1 ring-[#f5b301]/45"
                    >
                      Open this listing
                    </a>
                  )}
                </div>
                {!n.is_read && (
                  <button onClick={() => markRead(n.id)} className="text-xs text-brand hover:underline">
                    Mark read
                  </button>
                )}
              </div>
            </Card>
            );
          })}
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
