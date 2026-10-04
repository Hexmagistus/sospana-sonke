"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Card, Field, Input, Button, Alert } from "@/components/ui";
import { GlowFrame } from "@/components/HighTech";
import { CircuitMascot, GreetingLine, friendlyAuthError } from "@/components/AuthDelight";
import { api, ApiError } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState("");
  const [devToken, setDevToken] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSent("");
    setDevToken(null);
    setBusy(true);
    try {
      const res = await api.post<{ status: string; reset_token?: string | null }>(
        "/auth/password-reset/request",
        { email },
      );
      setSent(res.status);
      setDevToken(res.reset_token || null);
    } catch (err) {
      setError(friendlyAuthError(err instanceof ApiError ? err.message : "Could not send the reset just then."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative -mx-4 -mt-6 overflow-hidden px-4 pb-16 pt-10 sm:pt-14">
      <Image src="/photos/cape-town-coast.jpg" alt="" fill priority sizes="100vw" className="object-cover object-center" />
      <div className="auth-stage-scrim absolute inset-0" />
      <div className="pointer-events-none absolute inset-0 bg-noise opacity-20 mix-blend-overlay" />
      <div className="relative mx-auto max-w-md">
        <GreetingLine />
        <div className="mb-4 flex justify-center">
          <CircuitMascot coverEyes={false} celebrate={Boolean(sent)} />
        </div>
        <h1 className="mb-2 text-center text-3xl font-extrabold text-ss-text">Reset your password</h1>
        <p className="mb-5 text-center text-sm text-ss-muted">
          We&apos;ll send a token if that email is registered. The reply looks the same either way, so nobody can use this to check who has an account.
        </p>
        <GlowFrame>
          <Card className="auth-panel">
            <form onSubmit={submit} className="space-y-4">
              {error && <Alert kind="error" onPhoto>{error}</Alert>}
              {sent && <Alert kind="success">{sent} Open the email and paste the token on the next screen.</Alert>}
              <Field label="Email">
                <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
              </Field>
              <Button type="submit" loading={busy} disabled={busy} glow className="w-full">
                {busy ? "Sending…" : "Send reset token"}
              </Button>
            </form>
            <p className="mt-4 text-center text-sm text-ss-muted">
              <Link href="/login" className="text-brand hover:underline">Back to sign in</Link>
              {devToken && (
                <>
                  {" · "}
                  <Link href={`/reset-password?token=${encodeURIComponent(devToken)}`} className="text-brand hover:underline">
                    Continue with this token
                  </Link>
                </>
              )}
              {!devToken && sent && (
                <>
                  {" · "}
                  <Link href="/reset-password" className="text-brand hover:underline">I have a token</Link>
                </>
              )}
            </p>
          </Card>
        </GlowFrame>
      </div>
    </div>
  );
}
