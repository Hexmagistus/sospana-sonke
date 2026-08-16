"use client";

import { useState } from "react";
import Guard from "@/components/Guard";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { Card, Field, Input, Button, Alert } from "@/components/ui";

function SecurityInner() {
  const { user, refreshUser } = useAuth();
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

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Security</h1>
      {msg && <Alert kind="success">{msg}</Alert>}
      {err && <Alert kind="error">{err}</Alert>}

      <Card>
        <h2 className="mb-2 text-lg font-semibold">Two-factor authentication (TOTP)</h2>
        <p className="mb-4 text-sm text-gray-500">
          Status: {user?.mfa_enabled ? <b className="text-green-700">Enabled</b> : <b>Disabled</b>}
        </p>

        {!user?.mfa_enabled && !setup && <Button onClick={begin}>Set up MFA</Button>}

        {!user?.mfa_enabled && setup && (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">
              Add this secret to your authenticator app, then enter the current 6-digit code.
            </p>
            <code className="block break-all rounded bg-gray-100 px-3 py-2 text-sm">{setup.secret}</code>
            <p className="break-all text-xs text-gray-400">{setup.otpauth_uri}</p>
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
