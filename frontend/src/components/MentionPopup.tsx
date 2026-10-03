"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import NoticeLink from "@/components/NoticeLink";
import type { Notification } from "@/lib/types";

/** Pop-up on sign-in (and while browsing) telling a member they were tagged in a tip. */
export default function MentionPopup() {
  const { user, loading } = useAuth();
  const [notes, setNotes] = useState<Notification[]>([]);

  useEffect(() => {
    if (loading || !user) { setNotes([]); return; }
    api.get<Notification[]>("/notifications?unread_only=true&limit=50")
      .then((all) => setNotes(all.filter((n) => n.type === "mention")))
      .catch(() => {});
  }, [user, loading]);

  if (!user || notes.length === 0) return null;

  async function dismiss() {
    const ids = notes.map((n) => n.id);
    setNotes([]);
    await Promise.all(ids.map((id) => api.post(`/notifications/${id}/read`).catch(() => {})));
    window.dispatchEvent(new Event("notifications:changed"));
  }

  const first = notes[0];
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-navy/40 p-4 backdrop-blur-sm">
      <div role="dialog" aria-modal="true" aria-label="You were tagged"
        className="w-full max-w-sm overflow-hidden rounded-2xl bg-ss-surface shadow-xl">
        <NoticeLink note={first} variant="plain" onActivate={() => { void dismiss(); }}>
          <span className="block text-2xl" aria-hidden="true">🔔</span>
          <span className="mt-1 block text-lg font-bold text-ss-text">You were tagged!</span>
          <span className="mt-2 block text-sm font-medium text-ss-text">{first.title}</span>
          {first.body && <span className="mt-1 block break-words text-sm text-ss-muted">“{first.body}”</span>}
          {notes.length > 1 && (
            <span className="mt-2 block text-xs text-ss-muted">
              +{notes.length - 1} more tag{notes.length > 2 ? "s" : ""} in your notifications.
            </span>
          )}
          <span className="mt-4 inline-flex min-h-11 items-center rounded-lg bg-navy px-3 text-sm font-semibold text-white">
            View
          </span>
        </NoticeLink>
        <div className="px-4 pb-4">
          <button
            type="button"
            onClick={() => { void dismiss(); }}
            className="inline-flex min-h-11 items-center rounded-lg bg-ss-primary-soft px-3 text-sm font-semibold text-ss-text hover:bg-ss-primary-soft-strong"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}
