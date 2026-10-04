"use client";

import { useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api } from "@/lib/api";
import type { Notification } from "@/lib/types";
import NoticeLink from "@/components/NoticeLink";

function BellIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 9a6 6 0 1 1 12 0c0 7 3 7 3 7H3s3 0 3-7" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M10 19a2 2 0 0 0 4 0" />
    </svg>
  );
}

/** Recent notices, each one a link to its own target. */
export default function NotificationBell({ unread }: { unread: number }) {
  const [open, setOpen] = useState(false);
  const [notes, setNotes] = useState<Notification[]>([]);
  const [err, setErr] = useState("");
  const panelId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const pathname = usePathname();

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    api.get<Notification[]>("/notifications?limit=8")
      .then((rows) => { if (!cancelled) { setNotes(rows); setErr(""); } })
      .catch((e: Error) => { if (!cancelled) setErr(e.message || "Couldn't load notifications"); });
    return () => { cancelled = true; };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    }
    function onPointer(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onPointer);
    };
  }, [open]);

  const label = unread > 0 ? `Notifications, ${unread > 9 ? "9+" : unread} unread` : "Notifications";

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={buttonRef}
        type="button"
        className="relative flex h-11 w-[2.3rem] items-center min-[400px]:w-11 justify-center rounded-full text-ss-text transition hover:bg-ss-primary-soft"
        aria-label={label}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
      >
        <BellIcon />
        {unread > 0 && (
          <span className="absolute right-1 top-1 inline-flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-red-700 px-1 text-[10px] font-bold leading-none text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>
      {open && (
        <div
          id={panelId}
          role="dialog"
          aria-label="Recent notifications"
          className="fixed inset-x-3 top-[4.5rem] z-50 max-h-[70vh] overflow-y-auto rounded-2xl border border-ss-border bg-ss-surface p-2 text-ss-text shadow-xl lg:absolute lg:inset-x-auto lg:right-0 lg:top-full lg:mt-2 lg:w-[min(22rem,calc(100vw-2rem))]"
        >
          {err && <p className="px-3 py-2 text-sm text-ss-danger">{err}</p>}
          {!err && notes.length === 0 && (
            <p className="px-3 py-3 text-sm text-ss-muted">No notifications yet.</p>
          )}
          <ul className="space-y-1">
            {notes.map((n) => (
              <li key={n.id}>
                <NoticeLink note={n} variant="row" onActivate={() => setOpen(false)} className={n.is_read ? "opacity-60" : ""}>
                  <span className="block text-sm font-medium">{n.title}</span>
                  {!n.is_read && <span className="text-[11px] font-semibold uppercase tracking-wide text-ss-primary">Unread</span>}
                </NoticeLink>
              </li>
            ))}
          </ul>
          <Link
            href="/notifications"
            onClick={() => setOpen(false)}
            className="mt-1 block min-h-11 rounded-xl px-3 py-2.5 text-center text-sm font-semibold text-ss-text hover:bg-ss-primary-soft"
          >
            See all notifications
          </Link>
        </div>
      )}
    </div>
  );
}
