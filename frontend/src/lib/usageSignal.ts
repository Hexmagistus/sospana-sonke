"use client";

import { API_BASE } from "@/lib/api";

export type PrivacyNavigator = {
  doNotTrack?: string | null;
  globalPrivacyControl?: boolean;
};

/** Do Not Track or Global Privacy Control. The search still runs; the count does not. */
export function privacyOptOut(nav: PrivacyNavigator | null | undefined): boolean {
  if (!nav) return false;
  return nav.doNotTrack === "1" || nav.globalPrivacyControl === true;
}

export function privacyHeaders(nav: PrivacyNavigator | null | undefined): HeadersInit {
  if (!privacyOptOut(nav)) return {};
  return { "X-Privacy-Opt-Out": "1" };
}

export function recordOutboundClick(target: "employer" | "vacancy", id: string): void {
  if (typeof window === "undefined") return;
  if (privacyOptOut(window.navigator)) return;
  if (!id) return;
  void fetch(`${API_BASE}/intelligence/clicks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target, id }),
    keepalive: true,
    cache: "no-store",
    credentials: "omit",
  }).catch(() => undefined);
}
