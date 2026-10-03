"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

/**
 * One prompt for accounts that have never chosen tagging email. Dismissing it
 * remembers the dismissal. It does not turn email on or off.
 */
export default function TaggingChoiceBanner() {
  const { user, loading, refreshUser } = useAuth();
  const [hidden, setHidden] = useState(false);
  const [busy, setBusy] = useState(false);

  if (loading || hidden || !user?.show_tagging_banner) return null;

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
        When the Sospana Sonke team tags you, a notice stays inside your account.
        Email is off until you choose.
      </p>
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
