"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Card, Field, Input, Button, Alert } from "@/components/ui";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [needsOtp, setNeedsOtp] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password, otp);
      router.push("/dashboard");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Login failed";
      if (/mfa/i.test(msg)) {
        setNeedsOtp(true);
        setError("Enter your authenticator code to continue.");
      } else {
        setError(msg);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto mt-10 max-w-md">
      <h1 className="mb-1 text-center text-2xl font-bold text-brand">Sospana Sonke</h1>
      <p className="mb-6 text-center text-sm text-gray-500">
        We find the opportunities. We tailor your application.
      </p>
      <Card>
        <h2 className="mb-4 text-lg font-semibold">Sign in</h2>
        <form onSubmit={submit} className="space-y-4">
          {error && <Alert kind="error">{error}</Alert>}
          <Field label="Email">
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </Field>
          <Field label="Password">
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </Field>
          {needsOtp && (
            <Field label="Authenticator code">
              <Input value={otp} onChange={(e) => setOtp(e.target.value)} inputMode="numeric" placeholder="6-digit code" />
            </Field>
          )}
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-gray-500">
          No account?{" "}
          <Link href="/register" className="text-brand hover:underline">
            Create one
          </Link>
        </p>
      </Card>
    </div>
  );
}
