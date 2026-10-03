"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { PREFERENCES_HREF } from "@/lib/notificationTarget";

function word(state: string | undefined) {
  if (state === "yes") return "Yes";
  if (state === "no") return "No";
  return "Not chosen";
}

/**
 * One prompt for accounts that have never chosen tagging, contact by post,
 * or alerts. The banner opens the preferences page. Not now only hides it
 * and does not record a yes or a no.
 */
export default function TaggingChoiceBanner() {
  const { user, loading, refreshUser } = useAuth();
  const [hidden, setHidden] = useState(false);
  const [busy, setBusy] = useState(false);

  if (loading || hidden || !user?.show_consent_banner) return null;

  async function later() {
    setBusy(true);
    try {
      await api.post("/account/tagging-banner/dismiss");
      setHidden(true);
      await refreshUser();
    } catch {
      setBusy(false);
    }
  }

  return (
    <div className="fixed bottom-24 left-4 right-4 z-40 mx-auto max-w-xl md:bottom-6">
      <div className="relative rounded-2xl border border-ss-primary/40 bg-ss-surface/95 shadow-lg backdrop-blur-sm">
        <Link
          href={PREFERENCES_HREF}
          className="block min-h-11 rounded-2xl p-4 pr-4 pb-16 text-ss-text transition hover:bg-ss-primary-soft"
        >
          <span className="block text-sm">
            Sospana Sonke needs your three contact choices. Email stays off until you say yes.
          </span>
          <span className="mt-2 block space-y-1 text-sm text-ss-muted">
            <span className="block">Tagging: {word(user?.tagging_state)}</span>
            <span className="block">Preferred post: {word(user?.contact_by_post_state)}</span>
            <span className="block">Alerts: {word(user?.alerts_state)}</span>
          </span>
          <span className="mt-3 inline-flex min-h-11 items-center rounded-lg bg-ss-primary px-3 text-sm font-semibold text-navy">
            Choose
          </span>
        </Link>
        <button
          type="button"
          onClick={later}
          disabled={busy}
          className="absolute bottom-3 right-3 inline-flex min-h-11 items-center rounded-lg px-3 text-sm font-semibold text-ss-muted hover:bg-ss-primary-soft hover:text-ss-text disabled:opacity-50"
        >
          Not now
        </button>
      </div>
    </div>
  );
}
