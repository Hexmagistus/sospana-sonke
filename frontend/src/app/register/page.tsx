"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Card, Field, Input, Select, Button, Alert } from "@/components/ui";
import { POST_TYPES } from "@/lib/preferences";
import { WhatsAppChannelButton } from "@/components/WhatsAppChannel";
import { CircuitOverlay, GlowFrame, LogoGlow } from "@/components/HighTech";
import { CircuitMascot, GreetingLine, LitCircuits, PasswordMeter, friendlyAuthError, successPause } from "@/components/AuthDelight";

function YesNo({
  name, label, value, onChange,
}: { name: string; label: string; value: boolean | null; onChange: (next: boolean) => void }) {
  return (
    <div role="radiogroup" aria-label={label} className="text-sm text-ss-text">
      <span className="mb-1 block text-ss-muted">{label}</span>
      <div className="flex gap-5">
        <label className="flex min-h-11 items-center gap-2">
          <input type="radio" name={name} checked={value === true} onChange={() => onChange(true)} /> Yes
        </label>
        <label className="flex min-h-11 items-center gap-2">
          <input type="radio" name={name} checked={value === false} onChange={() => onChange(false)} /> No
        </label>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({
    first_name: "", last_name: "", email: "", password: "", mobile_number: "",
    preferred_position: "", qualification_name: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [consent, setConsent] = useState(false);
  // null = left unanswered, which stays "not chosen yet" on the server.
  const [alerts, setAlerts] = useState<boolean | null>(null);
  const [tagging, setTagging] = useState<boolean | null>(null);
  const [postType, setPostType] = useState("");
  const [passwordFocused, setPasswordFocused] = useState(false);
  const [celebrate, setCelebrate] = useState(false);

  function set(k: string, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!consent) {
      setError("Please accept the Privacy Policy and Terms to create your account.");
      return;
    }
    setBusy(true);
    try {
      await register({
        ...form,
        accepted_policy: true,
        ...(tagging === null ? {} : { allow_tagging: tagging }),
        ...(postType ? { preferred_post_type: postType } : {}),
        ...(alerts === null ? {} : { notify_opportunity_alerts: alerts }),
      });
      setCelebrate(true);
      setBusy(false);
      await successPause();
      router.push("/companies");
    } catch (err) {
      setBusy(false);
      setError(friendlyAuthError(err instanceof Error ? err.message : "Registration failed"));
    }
  }

  const filled = [
    form.first_name, form.last_name, form.email, form.password, form.preferred_position,
  ].filter((v) => v.trim()).length;

  return (
    <div className="relative -mx-4 -mt-6 overflow-hidden px-4 pb-16 pt-10 sm:pt-14">
      <Image
        src="/photos/cape-town-mountain.jpg"
        alt=""
        fill
        priority
        sizes="100vw"
        className="object-cover object-[center_30%]"
      />
      <div className="auth-stage-scrim absolute inset-0" />
      <div className="pointer-events-none absolute inset-0 bg-noise opacity-20 mix-blend-overlay" />
      <div className="relative mx-auto max-w-md">
      <CircuitOverlay className="-z-10 opacity-40" opacity={0.12} stroke="#f5b301" dotColor="#f5b301" />
      <GreetingLine />
      <div className="mb-4 flex items-center justify-center gap-4">
        <LogoGlow>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo-mark.png" alt="Sospana Sonke" className="block h-24 w-24 max-w-none shrink-0 aspect-square rounded-2xl object-cover shadow-[0_0_44px_-4px_var(--ss-primary-glow)] ring-1 ring-ss-primary/30" />
        </LogoGlow>
        <CircuitMascot coverEyes={passwordFocused && !celebrate} celebrate={celebrate} />
      </div>
      <LitCircuits lit={filled + (consent ? 1 : 0)} total={6} />
      <h1 className="animate-gradient-text mb-1 bg-gradient-to-r from-[#22d3ee] via-[#f5b301] to-[#a78bfa] bg-clip-text text-center text-4xl font-extrabold text-transparent [filter:drop-shadow(0_0_16px_rgba(245,179,1,0.45))]">Create your account</h1>
      <p className="mb-2 text-center text-xs font-semibold uppercase tracking-[0.16em] text-[#ffcf5a]">Born in SADC, built for the world</p>
      <p className="mb-5 text-center text-base font-medium text-blue-100">Free forever. Takes about 60 seconds. Your future self says thanks. 🚀</p>
      <div className="mb-6">
        <Alert kind="info" onPhoto>
          First sign-in taking a while? That&apos;s just our server being woken up (or occasionally updated)
          behind the scenes — it can take a minute or two, not a sign anything&apos;s wrong.
        </Alert>
      </div>
      {celebrate && (
        <p className="mb-3 text-center text-sm font-semibold text-[#ffcf5a]" role="status">
          Account&apos;s open. Taking you to the directory…
        </p>
      )}
      <GlowFrame>
        <Card className="auth-panel">
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
            <Field label="Role you're looking for">
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
              <Input
                type="password"
                value={form.password}
                onChange={(e) => set("password", e.target.value)}
                onFocus={() => setPasswordFocused(true)}
                onBlur={() => setPasswordFocused(false)}
                autoComplete="new-password"
                required
                minLength={8}
              />
              <PasswordMeter password={form.password} />
            </Field>
            <label className="flex items-start gap-2 text-sm text-ss-muted">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-1 h-4 w-4 shrink-0 accent-[#f5b301]"
                required
              />
              <span>
                I have read the{" "}
                <Link href="/privacy" target="_blank" className="text-brand hover:underline">Privacy Policy</Link>{" "}
                and{" "}
                <Link href="/terms" target="_blank" className="text-brand hover:underline">Terms</Link>, and I agree
                that Sospana Sonke may process my personal information to match me to vacancies, as described there (POPIA).
              </span>
            </label>
            <fieldset className="space-y-4 rounded-xl border border-ss-border p-3">
              <legend className="px-1 text-sm font-semibold text-ss-text">Optional: your preferences</legend>
              <p className="text-xs text-ss-muted">
                Each choice is separate and optional. Anything you leave unanswered stays &ldquo;not chosen&rdquo;
                and we will remind you to choose. Nothing is switched on for you. You can change these later on the Preferences page.
              </p>
              <YesNo
                name="tagging"
                label="May an administrator tag you to employers?"
                value={tagging}
                onChange={setTagging}
              />
              <label className="block text-sm text-ss-text">
                <span className="mb-1 block text-ss-muted">What kind of post would you like to be considered for?</span>
                <Select value={postType} onChange={(e) => setPostType(e.target.value)}>
                  <option value="">Choose later</option>
                  {POST_TYPES.map((p) => (
                    <option key={p.value} value={p.value}>{p.label}</option>
                  ))}
                </Select>
              </label>
              <YesNo
                name="alerts"
                label="May we send you alerts about posts that match you?"
                value={alerts}
                onChange={setAlerts}
              />
            </fieldset>
            <Button type="submit" loading={busy} disabled={busy || !consent} glow className="w-full">
              {busy ? "Creating…" : "Create account"}
            </Button>
          </form>
          <div className="mt-5 border-t border-ss-border pt-4 text-center">
            <p className="mb-2 text-sm text-ss-muted">
              Want vacancy alerts on WhatsApp? Optional — no number needed, and it never touches your account.
            </p>
            <WhatsAppChannelButton source="register" className="w-full" />
          </div>
          <p className="mt-4 text-center text-sm text-ss-muted">
            Already registered?{" "}
            <Link href="/login" className="text-brand hover:underline">
              Sign in
            </Link>
            {" · "}
            <Link href="/forgot-password" className="text-brand hover:underline">
              Forgot password
            </Link>
          </p>
        </Card>
      </GlowFrame>
      </div>
    </div>
  );
}
