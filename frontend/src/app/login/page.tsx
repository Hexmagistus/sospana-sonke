"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Card, Field, Input, Button, Alert } from "@/components/ui";
import { CircuitOverlay, GlowFrame, LogoGlow } from "@/components/HighTech";
import { CircuitMascot, GreetingLine, LitCircuits, friendlyAuthError, successPause } from "@/components/AuthDelight";
import { api } from "@/lib/api";
import { LoginAdRail } from "@/lib/explorer/AdSlot";
import { AdApplyDialog } from "@/lib/explorer/AdApplyDialog";
import type { PublicAd } from "@/lib/explorer/adSlots";

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

function AuthLoader() {
  const messages = [
    "Signing you in…",
    "Waking up the server — the first sign-in after a quiet spell can take up to a minute…",
    "Getting your opportunities ready…",
    "Almost there…",
  ];
  const [pct, setPct] = useState(8);
  const [mi, setMi] = useState(0);
  useEffect(() => {
    const start = Date.now();
    const id = setInterval(() => {
      const t = (Date.now() - start) / 1000;
      setPct(Math.min(96, 8 + 88 * (1 - Math.exp(-t / 16))));
      setMi(t > 40 ? 3 : t > 20 ? 2 : t > 6 ? 1 : 0);
    }, 200);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-ss-glass px-6 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-2xl border border-ss-border bg-ss-surface p-8 text-center shadow-xl">
        <svg viewBox="0 0 50 50" className="auth-spin mx-auto mb-5 h-14 w-14 animate-spin" style={{ animationDuration: "1.1s" }}>
          <circle cx="25" cy="25" r="20" fill="none" stroke="var(--ss-border)" strokeWidth="5" />
          <circle cx="25" cy="25" r="20" fill="none" stroke="#0f766e" strokeWidth="5" strokeLinecap="round" strokeDasharray="90 160" />
        </svg>
        <p className="mb-1 font-semibold text-ss-text">{messages[mi]}</p>
        <p className="mb-5 text-xs text-ss-muted">This can take up to a minute the first time — hang tight.</p>
        <div className="h-2 w-full overflow-hidden rounded-full bg-ss-border">
          <div className="h-full rounded-full transition-all duration-200 ease-out"
               style={{ width: pct + "%", background: "#0f766e" }} />
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  const { login, loginWithGoogle } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [needsOtp, setNeedsOtp] = useState(false);
  const [googleCredential, setGoogleCredential] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [authing, setAuthing] = useState(false);
  const [passwordFocused, setPasswordFocused] = useState(false);
  const [celebrate, setCelebrate] = useState(false);
  // The four advertiser spots: approved ads only (none are seeded); empty spots invite advertisers.
  const [ads, setAds] = useState<PublicAd[]>([]);
  const [applyFor, setApplyFor] = useState<string | null | undefined>(undefined);
  useEffect(() => {
    let cancelled = false;
    api.get<PublicAd[]>("/ads/slots").then((r) => { if (!cancelled) setAds(r); }).catch(() => { /* empty spots still show */ });
    return () => { cancelled = true; };
  }, []);

  // Load Google Identity Services and render the "Sign in with Google" button,
  // only when a client ID is configured (otherwise the feature stays hidden).
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => {
      const g = (window as unknown as { google?: any }).google; // eslint-disable-line @typescript-eslint/no-explicit-any
      if (!g?.accounts?.id) return;
      g.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async (resp: { credential: string }) => {
          setError("");
          setAuthing(true);
          try {
            await loginWithGoogle(resp.credential);
            setCelebrate(true);
            setAuthing(false);
            await successPause();
            router.push("/companies");
          } catch (err) {
            const msg = err instanceof Error ? err.message : "Google sign-in failed.";
            setAuthing(false);
            if (/mfa/i.test(msg)) {
              setGoogleCredential(resp.credential);
              setNeedsOtp(true);
              setError("Enter your authenticator code to continue.");
            } else {
              setError(msg);
            }
          }
        },
      });
      const el = document.getElementById("google-signin-btn");
      if (el) g.accounts.id.renderButton(el, { theme: "outline", size: "large", width: 320, text: "signin_with", shape: "rectangular" });
    };
    document.body.appendChild(script);
    return () => { script.remove(); };
  }, [loginWithGoogle, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    setAuthing(true);
    try {
      if (googleCredential) await loginWithGoogle(googleCredential, otp);
      else await login(email, password, otp);
      setCelebrate(true);
      setAuthing(false);
      setBusy(false);
      await successPause();
      router.push("/companies");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Login failed";
      setAuthing(false);
      setBusy(false);
      if (/mfa/i.test(msg)) {
        setNeedsOtp(true);
        setError("Enter your authenticator code to continue.");
      } else {
        setError(friendlyAuthError(msg));
      }
    }
  }

  return (
    <div className="relative -mx-4 -mt-6 overflow-hidden px-4 pb-16 pt-10 sm:pt-14">
      <Image
        src="/photos/cape-town-coast.jpg"
        alt=""
        fill
        priority
        sizes="100vw"
        className="object-cover object-center"
      />
      <div className="auth-stage-scrim absolute inset-0" />
      <div className="pointer-events-none absolute inset-0 bg-noise opacity-20 mix-blend-overlay" />
      {/* Form column in the middle; on xl two ad spots sit each side of it, below xl they follow the form. */}
      <div className="relative mx-auto grid max-w-md gap-6 xl:max-w-none xl:grid-cols-[minmax(0,15rem)_minmax(0,28rem)_minmax(0,15rem)] xl:justify-center xl:gap-10">
      <div className="min-w-0 xl:col-start-2 xl:row-start-1">
      {authing && <AuthLoader />}
      <CircuitOverlay className="-z-10 opacity-40" opacity={0.12} stroke="#0b2447" dotColor="#f5b301" />
      <p className="mb-3 text-center text-xs font-semibold uppercase tracking-[0.18em] text-ss-primary">Born in SADC, built for the world</p>
      <GreetingLine />
      <div className="mb-4 flex items-center justify-center gap-4">
        <div className="auth-float">
          <LogoGlow>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo-mark.png" alt="Sospana Sonke" className="block h-24 w-24 max-w-none shrink-0 aspect-square rounded-2xl object-cover shadow-[0_0_44px_-4px_var(--ss-primary-glow)] ring-1 ring-ss-primary/30" />
          </LogoGlow>
        </div>
        <CircuitMascot coverEyes={passwordFocused && !celebrate} celebrate={celebrate} />
      </div>
      <LitCircuits
        lit={(email.trim() ? 1 : 0) + (password ? 1 : 0) + (needsOtp && otp.trim() ? 1 : 0)}
        total={needsOtp ? 3 : 2}
      />
      <h1 className="animate-gradient-text mb-1 bg-gradient-to-r from-[#0b2447] via-[#8a5a00] to-[#5b3fd6] bg-clip-text text-center text-4xl font-extrabold text-transparent ">Sospana Sonke</h1>
      <p className="mb-4 text-center text-base font-medium text-ss-muted">
        We find the opportunities. You apply direct. <span className="font-bold text-ss-tech">No middle-man, no fees, no nonsense.</span> 😎
      </p>
      <div className="mb-6">
        <Alert kind="info" onPhoto>
          Sign-in taking a while? That&apos;s just our server being woken up (or occasionally updated) behind the
          scenes — it can take a minute or two, not a sign anything&apos;s wrong.
        </Alert>
      </div>
      {celebrate && (
        <p className="mb-3 text-center text-sm font-semibold text-ss-primary" role="status">
          You&apos;re in. Opening the directory…
        </p>
      )}
      <GlowFrame>
        <Card className="auth-panel">
          <h2 className="text-2xl font-extrabold">Sign in</h2>
          <p className="mb-4 mt-1 text-sm text-ss-muted">Welcome back — your opportunities missed you. 👋</p>
          <form onSubmit={submit} className="space-y-4">
            {error && <Alert kind="error">{error}</Alert>}
            <Field label="Email">
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required={!googleCredential} />
            </Field>
            <Field label="Password">
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onFocus={() => setPasswordFocused(true)}
                onBlur={() => setPasswordFocused(false)}
                autoComplete="current-password"
                required={!googleCredential}
              />
            </Field>
            {needsOtp && (
              <Field label="Authenticator code">
                <Input value={otp} onChange={(e) => setOtp(e.target.value)} inputMode="numeric" placeholder="6-digit code" />
              </Field>
            )}
            <Button type="submit" loading={busy} disabled={busy} glow className="w-full">
              {busy ? "Signing in…" : "Sign in"}
            </Button>
            <p className="text-center text-sm">
              <Link href="/forgot-password" className="text-brand hover:underline">
                Forgot password?
              </Link>
            </p>
          </form>

          {GOOGLE_CLIENT_ID && (
            <div className="mt-5">
              <div className="mb-4 flex items-center gap-3">
                <span className="h-px flex-1 bg-ss-border" />
                <span className="text-xs font-medium uppercase tracking-wider text-ss-muted">or</span>
                <span className="h-px flex-1 bg-ss-border" />
              </div>
              <div className="flex justify-center">
                <div id="google-signin-btn" />
              </div>
            </div>
          )}

          <p className="mt-4 text-center text-sm text-ss-muted">
            No account?{" "}
            <Link href="/register" className="text-brand hover:underline">
              Create one
            </Link>
          </p>
        </Card>
      </GlowFrame>
      </div>
      <LoginAdRail side="left" ads={ads} onApply={setApplyFor} className="xl:col-start-1 xl:row-start-1 xl:self-center" />
      <LoginAdRail side="right" ads={ads} onApply={setApplyFor} className="xl:col-start-3 xl:row-start-1 xl:self-center" />
      </div>
      {applyFor !== undefined && <AdApplyDialog slotKey={applyFor} onClose={() => setApplyFor(undefined)} />}
    </div>
  );
}
