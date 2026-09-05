"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Card, Field, Input, Button, Alert } from "@/components/ui";

// Ndebele-art-inspired decorative border bands (bold black-outlined geometric
// triangles in bright alternating colors, echoing the mural/beadwork tradition
// of the amaNdebele) framing the sign-in card top and bottom.
const NDEBELE_ROWS: { bg: string; tri: string }[] = [
  { bg: "#e4322b", tri: "#f5b301" }, // red / gold
  { bg: "#0b1f3a", tri: "#2f9bf6" }, // navy / sky
  { bg: "#1a9e5f", tri: "#ff7a1a" }, // green / sun
];

function NdebeleStrip({ id, flip = false, className = "" }: { id: string; flip?: boolean; className?: string }) {
  const rows = flip ? [...NDEBELE_ROWS].reverse() : NDEBELE_ROWS;
  return (
    <div className={`flex flex-col ${className}`} aria-hidden="true">
      {rows.map((row, i) => (
        <svg key={i} viewBox="0 0 200 18" preserveAspectRatio="none" className="block h-4 w-full">
          <defs>
            <pattern id={`${id}-tri-${i}`} width="18" height="18" patternUnits="userSpaceOnUse">
              <rect width="18" height="18" fill={row.bg} />
              <polygon
                points={flip ? "0,18 9,0 18,18" : "0,0 9,18 18,0"}
                fill={row.tri}
                stroke="#161616"
                strokeWidth="1"
                strokeLinejoin="round"
              />
            </pattern>
          </defs>
          <rect width="200" height="18" fill={`url(#${id}-tri-${i})`} />
        </svg>
      ))}
    </div>
  );
}

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

export default function LoginPage() {
  const { login, loginWithGoogle } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [needsOtp, setNeedsOtp] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

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
          try {
            await loginWithGoogle(resp.credential);
            router.push("/companies");
          } catch (err) {
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
    }
  }

  return (
    <div className="mx-auto mt-10 max-w-md">
      <NdebeleStrip id="ndebele-login-top" className="mb-6 overflow-hidden rounded-t-xl shadow-sm" />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/logo-mark.png" alt="Sospana Sonke" className="mx-auto mb-3 h-16 w-16 rounded-2xl object-cover shadow-md" />
      <h1 className="mb-1 text-center text-2xl font-bold text-brand">Sospana Sonke</h1>
      <p className="mb-6 text-center text-sm text-gray-500">
        We find the opportunities. You apply direct.
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
          <Button type="submit" loading={busy} disabled={busy} className="w-full">
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
      <NdebeleStrip id="ndebele-login-bottom" flip className="mt-6 overflow-hidden rounded-b-xl shadow-sm" />
    </div>
  );
}
