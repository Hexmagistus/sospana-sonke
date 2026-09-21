"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Guard from "@/components/Guard";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { Card, Field, Input, Button, Alert } from "@/components/ui";

function SecurityInner() {
  const { user, refreshUser, logout } = useAuth();
  const router = useRouter();
  const [delPw, setDelPw] = useState("");
  const [delOpen, setDelOpen] = useState(false);
  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  async function begin() {
    setErr(""); setMsg("");
    try {
      setSetup(await api.post("/auth/mfa/setup"));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not start MFA setup");
    }
  }
  async function enable() {
    setErr(""); setMsg("");
    try {
      await api.post("/auth/mfa/enable", { code });
      setSetup(null); setCode(""); setMsg("MFA enabled.");
      await refreshUser();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Invalid code");
    }
  }
  async function disable() {
    setErr(""); setMsg("");
    try {
      await api.post("/auth/mfa/disable", { code });
      setCode(""); setMsg("MFA disabled.");
      await refreshUser();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Invalid code");
    }
  }

  async function exportData() {
    setErr(""); setMsg("");
    try {
      const data = await api.get<unknown>("/account/export");
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const a = document.createElement("a");
      a.href = url; a.download = "sospana-sonke-my-data.json"; a.click();
      URL.revokeObjectURL(url);
      setMsg("Your data export has been downloaded.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not export your data");
    }
  }
  async function deleteAccount() {
    setErr(""); setMsg("");
    try {
      await api.post("/account/delete", { password: delPw });
      logout();
      router.push("/login");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not delete your account");
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-ss-text">Security</h1>
      {msg && <Alert kind="success">{msg}</Alert>}
      {err && <Alert kind="error">{err}</Alert>}

      <Card>
        <h2 className="mb-2 text-lg font-semibold text-ss-text">Two-factor authentication (TOTP)</h2>
        <p className="mb-4 text-sm text-ss-muted">
          Status: {user?.mfa_enabled ? <b className="text-ss-success">Enabled</b> : <b className="text-ss-text">Disabled</b>}
        </p>

        {!user?.mfa_enabled && !setup && <Button onClick={begin}>Set up MFA</Button>}

        {!user?.mfa_enabled && setup && (
          <div className="space-y-3">
            <p className="text-sm text-ss-muted">
              Add this secret to your authenticator app, then enter the current 6-digit code.
            </p>
            <code className="block break-all rounded-lg border border-ss-border bg-ss-glass px-3 py-2 text-sm text-ss-text">{setup.secret}</code>
            <p className="break-all text-xs text-ss-muted">{setup.otpauth_uri}</p>
            <div className="flex items-end gap-2">
              <Field label="Authenticator code">
                <Input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" placeholder="6-digit" />
              </Field>
              <Button onClick={enable} disabled={!code}>Enable</Button>
            </div>
          </div>
        )}

        {user?.mfa_enabled && (
          <div className="flex items-end gap-2">
            <Field label="Authenticator code to disable">
              <Input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" placeholder="6-digit" />
            </Field>
            <Button variant="danger" onClick={disable} disabled={!code}>Disable MFA</Button>
          </div>
        )}
      </Card>

      <Card>
        <h2 className="mb-2 text-lg font-semibold text-ss-text">Your data (POPIA)</h2>
        <p className="mb-4 text-sm text-ss-muted">
          You have the right to see the personal information we hold about you and to have it deleted.
          Read our <a href="/privacy" className="text-brand hover:underline">Privacy Policy</a> for how we use it.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="secondary" onClick={exportData}>Download my data</Button>
          {!delOpen && <Button variant="danger" onClick={() => setDelOpen(true)}>Delete my account</Button>}
        </div>
        {delOpen && (
          <div className="mt-4 space-y-3 rounded-xl border border-ss-border p-4">
            <p className="text-sm text-ss-muted">
              This removes your messages and notifications immediately and anonymises your account. You will be signed out and
              cannot sign in again. This cannot be undone.
            </p>
            <div className="flex items-end gap-2">
              <Field label="Confirm with your password">
                <Input type="password" value={delPw} onChange={(e) => setDelPw(e.target.value)} autoComplete="current-password" />
              </Field>
              <Button variant="danger" onClick={deleteAccount} disabled={!delPw}>Permanently delete</Button>
              <Button variant="ghost" onClick={() => { setDelOpen(false); setDelPw(""); }}>Cancel</Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

export default function SecurityPage() {
  return (
    <Guard>
      <SecurityInner />
    </Guard>
  );
}
