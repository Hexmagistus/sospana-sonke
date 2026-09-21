"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

type Note = { id: string; type: string; title: string; body: string; link_url: string | null };

/** Pop-up on sign-in (and while browsing) telling a member they were tagged in a tip. */
export default function MentionPopup() {
  const { user, loading } = useAuth();
  const [notes, setNotes] = useState<Note[]>([]);

  useEffect(() => {
    if (loading || !user) { setNotes([]); return; }
    api.get<Note[]>("/notifications?unread_only=true&limit=50")
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
        className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
        <div className="text-2xl" aria-hidden="true">🔔</div>
        <h2 className="mt-1 text-lg font-bold text-navy">You were tagged!</h2>
        <p className="mt-2 text-sm font-medium text-gray-800">{first.title}</p>
        {first.body && <p className="mt-1 break-words text-sm text-gray-600">“{first.body}”</p>}
        {notes.length > 1 && <p className="mt-2 text-xs text-gray-500">+{notes.length - 1} more tag{notes.length > 2 ? "s" : ""} in your notifications.</p>}
        <div className="mt-4 flex gap-2">
          {first.link_url && (
            <Link href={first.link_url} onClick={dismiss}
              className="rounded-lg bg-navy px-3 py-2 text-sm font-semibold text-white">View</Link>
          )}
          <button onClick={dismiss} className="rounded-lg bg-gray-100 px-3 py-2 text-sm font-semibold text-gray-700">Got it</button>
        </div>
      </div>
    </div>
  );
}
