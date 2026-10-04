"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Card, Field, Input, Button, Alert } from "@/components/ui";
import { GlowFrame } from "@/components/HighTech";
import { CircuitMascot, GreetingLine, PasswordMeter, friendlyAuthError, successPause } from "@/components/AuthDelight";
import { api, ApiError } from "@/lib/api";

export default function ResetPasswordPage() {
  const params = useSearchParams();
  const [token, setToken] = useState(params.get("token") || "");
  const [password, setPassword] = useState("");
  const [again, setAgain] = useState("");
  const [focused, setFocused] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (password !== again) {
      setError("Those two passwords don't match. Type the new one twice.");
      return;
    }
    setBusy(true);
    try {
      await api.post("/auth/password-reset/confirm", { token: token.trim(), new_password: password });
      setDone(true);
      await successPause();
    } catch (err) {
      setError(friendlyAuthError(err instanceof ApiError ? err.message : "That reset didn't go through."));
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
          <CircuitMascot coverEyes={focused && !done} celebrate={done} />
        </div>
        <h1 className="mb-2 text-center text-3xl font-extrabold text-ss-text">Choose a new password</h1>
        <p className="mb-5 text-center text-sm text-ss-muted">
          Paste the token from the email. This signs out every other session on the account.
        </p>
        <GlowFrame>
          <Card className="auth-panel">
            {done ? (
              <div className="space-y-3 text-center">
                <Alert kind="success">Password updated. Sign in with the new one.</Alert>
                <Link href="/login" className="inline-block text-sm font-semibold text-brand hover:underline">
                  Back to sign in
                </Link>
              </div>
            ) : (
              <form onSubmit={submit} className="space-y-4">
                {error && <Alert kind="error" onPhoto>{error}</Alert>}
                <Field label="Reset token">
                  <Input value={token} onChange={(e) => setToken(e.target.value)} autoComplete="one-time-code" required />
                </Field>
                <Field label="New password (min 8 characters)">
                  <Input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onFocus={() => setFocused(true)}
                    onBlur={() => setFocused(false)}
                    autoComplete="new-password"
                    required
                    minLength={8}
                  />
                  <PasswordMeter password={password} />
                </Field>
                <Field label="Type it again">
                  <Input
                    type="password"
                    value={again}
                    onChange={(e) => setAgain(e.target.value)}
                    onFocus={() => setFocused(true)}
                    onBlur={() => setFocused(false)}
                    autoComplete="new-password"
                    required
                    minLength={8}
                  />
                </Field>
                <Button type="submit" loading={busy} disabled={busy} glow className="w-full">
                  {busy ? "Updating…" : "Update password"}
                </Button>
                <p className="text-center text-sm">
                  <Link href="/forgot-password" className="text-brand hover:underline">Need a new token?</Link>
                  {" · "}
                  <Link href="/login" className="text-brand hover:underline">Sign in</Link>
                </p>
              </form>
            )}
          </Card>
        </GlowFrame>
      </div>
    </div>
  );
}
