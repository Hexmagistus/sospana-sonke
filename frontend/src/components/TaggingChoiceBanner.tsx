"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

function word(state: string | undefined) {
  if (state === "yes") return "Yes";
  if (state === "no") return "No";
  return "Not chosen";
}

/**
 * One prompt for accounts that have never chosen tagging, contact by post,
 * or alerts. Dismissing it remembers the dismissal. It does not record a yes or a no.
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
    <div
      role="status"
      className="fixed bottom-24 left-4 right-4 z-40 mx-auto max-w-xl rounded-2xl border border-ss-primary/40 bg-ss-surface/95 p-4 shadow-lg backdrop-blur-sm md:bottom-6"
    >
      <p className="text-sm text-ss-text">
        Sospana Sonke needs your three contact choices. Email stays off until you say yes.
      </p>
      <ul className="mt-2 space-y-1 text-sm text-ss-muted">
        <li>Tagging: {word(user?.tagging_state)}</li>
        <li>Preferred post: {word(user?.contact_by_post_state)}</li>
        <li>Alerts: {word(user?.alerts_state)}</li>
      </ul>
      <div className="mt-3 flex flex-wrap gap-2">
        <Link
          href="/security#notification-preferences"
          className="rounded-lg bg-ss-primary px-3 py-1.5 text-sm font-semibold text-navy"
        >
          Choose
        </Link>
        <button
          type="button"
          onClick={later}
          disabled={busy}
          className="rounded-lg px-3 py-1.5 text-sm font-semibold text-ss-muted"
        >
          Not now
        </button>
      </div>
    </div>
  );
}
