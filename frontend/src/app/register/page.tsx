"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Card, Field, Input, Button, Alert } from "@/components/ui";
import { NdebeleStrip } from "@/components/NdebeleStrip";
import { CircuitOverlay, GlowFrame, LogoGlow } from "@/components/HighTech";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({
    first_name: "", last_name: "", email: "", password: "", mobile_number: "",
    preferred_position: "", qualification_name: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function set(k: string, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await register(form);
      router.push("/companies");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative mx-auto mt-10 max-w-md">
      <CircuitOverlay className="-z-10 opacity-70" opacity={0.1} stroke="#0b1f3a" dotColor="#f5b301" />
      <NdebeleStrip id="ndebele-register-top" glow className="mb-6 overflow-hidden rounded-t-xl shadow-sm" />
      <LogoGlow className="mx-auto mb-3 block w-fit">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo-mark.png" alt="Sospana Sonke" className="h-16 w-16 rounded-2xl object-cover shadow-md" />
      </LogoGlow>
      <h1 className="mb-4 text-center text-2xl font-bold text-brand">Create your account</h1>
      <div className="mb-6">
        <Alert kind="info">
          First sign-in taking a while? That&apos;s just our server being woken up (or occasionally updated)
          behind the scenes — it can take a minute or two, not a sign anything&apos;s wrong.
        </Alert>
      </div>
      <GlowFrame>
        <Card>
          <form onSubmit={submit} className="space-y-4">
            {error && <Alert kind="error">{error}</Alert>}
            <div className="grid grid-cols-2 gap-3">
              <Field label="First name">
                <Input value={form.first_name} onChange={(e) => set("first_name", e.target.value)} required />
              </Field>
              <Field label="Surname">
                <Input value={form.last_name} onChange={(e) => set("last_name", e.target.value)} required />
              </Field>
            </div>
            <Field label="Email">
              <Input type="email" value={form.email} onChange={(e) => set("email", e.target.value)} required />
            </Field>
            <Field label="Mobile number">
              <Input value={form.mobile_number} onChange={(e) => set("mobile_number", e.target.value)} />
            </Field>
            <Field label="Preferred post (the role you're looking for)">
              <Input
                value={form.preferred_position}
                onChange={(e) => set("preferred_position", e.target.value)}
                placeholder="e.g. Process Controller"
              />
            </Field>
            <Field label="Name of qualification">
              <Input
                value={form.qualification_name}
                onChange={(e) => set("qualification_name", e.target.value)}
                placeholder="e.g. National Diploma in Biotechnology"
              />
            </Field>
            <Field label="Password (min 8 characters)">
              <Input type="password" value={form.password} onChange={(e) => set("password", e.target.value)} required minLength={8} />
            </Field>
            <Button type="submit" loading={busy} disabled={busy} glow className="w-full">
              {busy ? "Creating…" : "Create account"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-gray-500">
            Already registered?{" "}
            <Link href="/login" className="text-brand hover:underline">
              Sign in
            </Link>
          </p>
        </Card>
      </GlowFrame>
      <NdebeleStrip id="ndebele-register-bottom" flip glow className="mt-6 overflow-hidden rounded-b-xl shadow-sm" />
    </div>
  );
}
