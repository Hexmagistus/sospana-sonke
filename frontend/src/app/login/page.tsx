"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Card, Field, Input, Button, Alert } from "@/components/ui";
import { NdebeleStrip } from "@/components/NdebeleStrip";
import { CircuitOverlay, GlowFrame, LogoGlow } from "@/components/HighTech";

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
    <div className="fixed inset-0 z-[100] flex items-center justify-center px-6 backdrop-blur-sm"
         style={{ background: "rgba(250,246,238,0.92)" }}>
      <div className="w-full max-w-sm rounded-2xl bg-white p-8 text-center shadow-xl">
        <svg viewBox="0 0 50 50" className="mx-auto mb-5 h-14 w-14 animate-spin" style={{ animationDuration: "1.1s" }}>
          <circle cx="25" cy="25" r="20" fill="none" stroke="#e5e7eb" strokeWidth="5" />
          <circle cx="25" cy="25" r="20" fill="none" stroke="#0f766e" strokeWidth="5" strokeLinecap="round" strokeDasharray="90 160" />
        </svg>
        <p className="mb-1 font-semibold" style={{ color: "#0b2a4a" }}>{messages[mi]}</p>
        <p className="mb-5 text-xs text-gray-400">This can take up to a minute the first time — hang tight.</p>
        <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
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
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [authing, setAuthing] = useState(false);

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
            router.push("/companies");
          } catch (err) {
            setAuthing(false);
            setError(err instanceof Error ? err.message : "Google sign-in failed.");
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
      await login(email, password, otp);
      router.push("/companies");
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
      setAuthing(false);
    }
  }

  return (
    <div className="relative mx-auto mt-10 max-w-md">
      {authing && <AuthLoader />}
      <CircuitOverlay className="-z-10 opacity-70" opacity={0.1} stroke="#0b1f3a" dotColor="#f5b301" />
      <NdebeleStrip id="ndebele-login-top" glow className="mb-6 overflow-hidden rounded-t-xl shadow-sm" />
      <LogoGlow className="mx-auto mb-3 block w-fit">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo-mark.png" alt="Sospana Sonke" className="h-16 w-16 rounded-2xl object-cover shadow-md" />
      </LogoGlow>
      <h1 className="mb-1 text-center text-2xl font-bold text-brand">Sospana Sonke</h1>
      <p className="mb-4 text-center text-sm text-gray-500">
        We find the opportunities. You apply direct.
      </p>
      <div className="mb-6">
        <Alert kind="info">
          Sign-in taking a while? That&apos;s just our server being woken up (or occasionally updated) behind the
          scenes — it can take a minute or two, not a sign anything&apos;s wrong.
        </Alert>
      </div>
      <GlowFrame>
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
            <Button type="submit" loading={busy} disabled={busy} glow className="w-full">
              {busy ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          {GOOGLE_CLIENT_ID && (
            <div className="mt-5">
              <div className="mb-4 flex items-center gap-3">
                <span className="h-px flex-1 bg-gray-200" />
                <span className="text-xs font-medium uppercase tracking-wider text-gray-400">or</span>
                <span className="h-px flex-1 bg-gray-200" />
              </div>
              <div className="flex justify-center">
                <div id="google-signin-btn" />
              </div>
            </div>
          )}

          <p className="mt-4 text-center text-sm text-gray-500">
            No account?{" "}
            <Link href="/register" className="text-brand hover:underline">
              Create one
            </Link>
          </p>
        </Card>
      </GlowFrame>
      <NdebeleStrip id="ndebele-login-bottom" flip glow className="mt-6 overflow-hidden rounded-b-xl shadow-sm" />
    </div>
  );
}
