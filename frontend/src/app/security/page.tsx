"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Guard from "@/components/Guard";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { Card, Field, Input, Button, Alert } from "@/components/ui";

function choiceWord(state: string | undefined) {
  if (state === "yes") return "Yes";
  if (state === "no") return "No";
  return "Not chosen";
}

function ChoiceRow({
  name, label, help, state, value, onChange,
}: {
  name: string;
  label: string;
  help: string;
  state?: string;
  value: boolean | null;
  onChange: (next: boolean) => void;
}) {
  return (
    <fieldset className="mt-4">
      <legend className="text-sm font-semibold text-ss-text">{label}</legend>
      <p className="text-sm text-ss-muted">{help}</p>
      <p className="mt-1 text-sm text-ss-text">Current: <b>{choiceWord(state)}</b></p>
      <div className="mt-2 flex gap-4 text-sm text-ss-text">
        <label className="flex items-center gap-2">
          <input type="radio" name={name} checked={value === true} onChange={() => onChange(true)} />
          Yes
        </label>
        <label className="flex items-center gap-2">
          <input type="radio" name={name} checked={value === false} onChange={() => onChange(false)} />
          No
        </label>
      </div>
    </fieldset>
  );
}

function SecurityInner() {
  const { user, refreshUser, logout } = useAuth();
  const router = useRouter();
  const [delPw, setDelPw] = useState("");
  const [delOpen, setDelOpen] = useState(false);
  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [tagging, setTagging] = useState<boolean | null>(null);
  const [byPost, setByPost] = useState<boolean | null>(null);
  const [alertsOn, setAlertsOn] = useState<boolean | null>(null);

  function picked(state: string | undefined, value: boolean | undefined): boolean | null {
    if (state === "yes") return true;
    if (state === "no") return false;
    return value === undefined ? null : null;
  }

  useEffect(() => {
    setTagging(picked(user?.tagging_state, user?.allow_tagging));
    setByPost(picked(user?.contact_by_post_state, user?.contact_by_post));
    setAlertsOn(picked(user?.alerts_state, user?.notify_opportunity_alerts));
  }, [user]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.location.hash !== "#notification-preferences") return;
    document.getElementById("notification-preferences")?.scrollIntoView({ block: "start" });
  }, [user]);

  async function savePreferences() {
    if (tagging === null || byPost === null || alertsOn === null) return;
    setErr(""); setMsg("");
    try {
      await api.put("/account/notification-preferences", {
        allow_tagging: tagging,
        contact_by_post: byPost,
        notify_opportunity_alerts: alertsOn,
      });
      await refreshUser();
      setMsg("Your three choices are saved.");
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "Could not save that choice");
    }
  }

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
  async function signOutEverywhere() {
    setErr(""); setMsg("");
    try {
      await api.post("/auth/logout-all");
      logout();
      router.push("/login");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not sign out other devices");
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
        <h2 className="mb-2 text-lg font-semibold text-ss-text">Signed-in devices</h2>
        <p className="mb-4 text-sm text-ss-muted">
          Lost a phone, or think someone else knows your password? Sign out of Sospana Sonke on every
          device at once, including this one. Resetting your password does this automatically too.
        </p>
        <Button variant="secondary" onClick={signOutEverywhere}>Sign out everywhere</Button>
      </Card>

      <Card>
        <div id="notification-preferences" className="scroll-mt-24">
        <h2 className="mb-2 text-lg font-semibold text-ss-text">Notification preferences</h2>
        <p className="mb-3 text-sm text-ss-muted">
          These are the same three choices as registration. A tag still appears inside this account.
          Email about a tag, or an alert, is sent only after you choose yes.
          Member messages are switched on from the <a href="/messages" className="text-brand hover:underline">Messages</a> page.
        </p>
        <ChoiceRow
          name="tagging"
          label="Tagging"
          help="An administrator may tag you for a vacancy."
          state={user?.tagging_state}
          value={tagging}
          onChange={setTagging}
        />
        <ChoiceRow
          name="post"
          label="Preferred post"
          help="We may contact you by post (mail)."
          state={user?.contact_by_post_state}
          value={byPost}
          onChange={setByPost}
        />
        <ChoiceRow
          name="alerts"
          label="Alerts"
          help="We may email you about roles that match the one you saved."
          state={user?.alerts_state}
          value={alertsOn}
          onChange={setAlertsOn}
        />
        <div className="mt-3">
          <Button onClick={savePreferences} disabled={tagging === null || byPost === null || alertsOn === null}>
            Save all three
          </Button>
        </div>
        </div>
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
