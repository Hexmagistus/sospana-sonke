"use client";

import { ReactNode } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { linkAttrs, notificationTarget, type NoticeInput } from "@/lib/notificationTarget";
import type { Notification } from "@/lib/types";

const CARD =
  "block min-h-11 w-full rounded-2xl border border-white/50 bg-ss-glass p-4 text-left text-ss-text shadow-sm transition hover:border-gold/80 hover:bg-ss-primary-soft focus-visible:border-gold dark:border-white/10";
const ROW =
  "block min-h-11 w-full rounded-xl px-3 py-2.5 text-left text-ss-text transition hover:bg-ss-primary-soft";
const PLAIN =
  "block min-h-11 w-full p-4 text-left text-ss-text transition hover:bg-ss-primary-soft";

function markRead(id: string) {
  void api.post(`/notifications/${id}/read`).then(() => {
    window.dispatchEvent(new Event("notifications:changed"));
  }).catch(() => {});
}

/**
 * The whole notice is one link or button. A tagged http(s) listing opens in
 * a new tab. Every other target stays in this tab. Activating it marks the
 * notice read.
 */
export default function NoticeLink({
  note,
  variant = "card",
  className = "",
  onActivate,
  children,
}: {
  note: Notification;
  variant?: "card" | "row" | "plain";
  className?: string;
  onActivate?: () => void;
  children: ReactNode;
}) {
  const target = notificationTarget(note as NoticeInput);
  const skin = variant === "card" ? CARD : variant === "row" ? ROW : PLAIN;
  const cls = `${skin} ${className}`;
  const hint = target.kind === "external"
    ? "Opens in a new tab"
    : target.kind === "download"
      ? "Downloads your report"
      : null;

  function activate() {
    if (!note.is_read) markRead(note.id);
    onActivate?.();
  }

  const body = (
    <>
      {children}
      {hint && <span className="mt-1 block text-xs font-semibold text-ss-text">{hint}</span>}
    </>
  );

  if (target.kind === "download") {
    return (
      <button
        type="button"
        className={cls}
        onClick={() => {
          activate();
          void api.download(target.href, "sospana-sonke-report.pdf").catch(() => {});
        }}
      >
        {body}
      </button>
    );
  }

  if (target.kind === "external") {
    const attrs = linkAttrs(target);
    return (
      <a href={target.href} {...attrs} className={cls} onClick={activate}>
        {body}
      </a>
    );
  }

  return (
    <Link href={target.href} className={cls} onClick={activate}>
      {body}
    </Link>
  );
}
