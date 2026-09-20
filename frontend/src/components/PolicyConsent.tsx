"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { POLICY_VERSION } from "@/lib/policy";
import { Button, Alert } from "@/components/ui";

/**
 * One-time POPIA consent gate. Shown to any signed-in user who has not accepted the
 * current Privacy Policy / Terms (accounts made before the consent checkbox existed,
 * Google sign-ups, or after a policy version bump). Hidden on the policy pages so the
 * user can read them first.
 */
export default function PolicyConsent() {
  const { user, loading, refreshUser, logout } = useAuth();
  const pathname = usePathname();
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (loading || !user || user.policy_version === POLICY_VERSION) return null;
  if (pathname === "/privacy" || pathname === "/terms") return null;

  async function accept() {
    setBusy(true);
    setError("");
    try {
      await api.post("/auth/accept-policy", {});
      await refreshUser();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save your choice. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="policy-consent-title"
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4"
    >
      <div className="w-full max-w-md rounded-2xl border border-ss-border bg-ss-surface p-6 shadow-xl">
        <h2 id="policy-consent-title" className="mb-2 text-xl font-bold text-ss-text">
          We&apos;ve updated our Privacy Policy
        </h2>
        <p className="mb-4 text-sm leading-relaxed text-ss-muted">
          To keep using Sospana Sonke, please review how we handle your personal information under
          South Africa&apos;s POPIA, and confirm you agree.
        </p>
        {error && <div className="mb-3"><Alert kind="error">{error}</Alert></div>}
        <label className="mb-4 flex items-start gap-2 text-sm text-ss-muted">
          <input
            type="checkbox"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
            className="mt-1 h-4 w-4 shrink-0 accent-[#f5b301]"
          />
          <span>
            I have read the{" "}
            <Link href="/privacy" className="text-brand hover:underline">Privacy Policy</Link> and{" "}
            <Link href="/terms" className="text-brand hover:underline">Terms</Link>, and I agree that
            Sospana Sonke may process my personal information as described there.
          </span>
        </label>
        <div className="flex gap-3">
          <Button onClick={accept} loading={busy} disabled={busy || !agreed} className="flex-1">
            Accept and continue
          </Button>
          <Button variant="secondary" onClick={logout} disabled={busy}>
            Sign out
          </Button>
        </div>
      </div>
    </div>
  );
}
