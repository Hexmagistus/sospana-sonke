"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { PREFERENCES_HREF } from "@/lib/notificationTarget";
import { needsBanner, postTypeLabel, yesNoLabel } from "@/lib/preferences";

/**
 * Shown to a signed-in client while any of the three preferences (tagging,
 * preferred post, alerts) is still "not chosen". It has no close button: the
 * only way to make it go away is to choose, on the preferences page. It is
 * hidden on that page itself so it never covers the form.
 */
export default function TaggingChoiceBanner() {
  const { user, loading } = useAuth();
  const pathname = usePathname();

  if (loading || !needsBanner(user) || pathname.startsWith(PREFERENCES_HREF)) return null;

  return (
    <div className="fixed bottom-24 left-4 right-4 z-40 mx-auto max-w-xl md:bottom-6" role="region" aria-label="Choose your preferences">
      <Link
        href={PREFERENCES_HREF}
        className="block min-h-11 rounded-2xl border border-ss-primary/40 bg-ss-surface/95 p-4 text-ss-text shadow-lg backdrop-blur-sm transition hover:bg-ss-primary-soft"
      >
        <span className="block text-sm font-semibold">Please choose your preferences</span>
        <span className="mt-1 block text-sm text-ss-muted">
          Nothing is switched on until you choose. This reminder stays until all three are chosen.
        </span>
        <span className="mt-2 block space-y-0.5 text-sm text-ss-muted">
          <span className="block">Tagging by an administrator: {yesNoLabel(user?.tagging_state)}</span>
          <span className="block">
            Preferred post: {user?.preferred_post_state === "chosen" ? postTypeLabel(user?.preferred_post_type) : "Not chosen"}
          </span>
          <span className="block">Alerts: {yesNoLabel(user?.alerts_state)}</span>
        </span>
        <span className="mt-3 inline-flex min-h-11 items-center rounded-lg bg-ss-primary px-3 text-sm font-semibold text-navy">
          Choose now
        </span>
      </Link>
    </div>
  );
}
