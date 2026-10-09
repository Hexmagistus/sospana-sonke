"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { Alert, Button, Card } from "@/components/ui";
import { POST_TYPES, postTypeLabel, unchosenCount, yesNoLabel } from "@/lib/preferences";
import type { User } from "@/lib/types";

type Field = "allow_tagging" | "preferred_post_type" | "notify_opportunity_alerts";

function StatusPill({ chosen, children }: { chosen: boolean; children: string }) {
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
        chosen ? "bg-brand/10 text-brand-dark" : "bg-gold/20 text-ss-text"
      }`}
    >
      {children}
    </span>
  );
}

function PreferencesInner() {
  const { user, refreshUser } = useAuth();
  const [tagging, setTagging] = useState<boolean | null>(null);
  const [alerts, setAlerts] = useState<boolean | null>(null);
  const [post, setPost] = useState<string>("");
  const [busy, setBusy] = useState<Field | null>(null);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  // Start each control from what is stored. "Not chosen" leaves it empty so
  // the person has to pick; nothing is pre-selected on their behalf.
  useEffect(() => {
    if (!user) return;
    setTagging(user.tagging_state === "yes" ? true : user.tagging_state === "no" ? false : null);
    setAlerts(user.alerts_state === "yes" ? true : user.alerts_state === "no" ? false : null);
    setPost(user.preferred_post_state === "chosen" ? user.preferred_post_type || "" : "");
  }, [user]);

  async function save(field: Field, value: boolean | string, done: string) {
    setErr(""); setMsg(""); setBusy(field);
    try {
      await api.put<User>("/account/notification-preferences", { [field]: value });
      await refreshUser();
      setMsg(done);
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "Could not save that choice");
    } finally {
      setBusy(null);
    }
  }

  if (user?.role === "admin") {
    return (
      <Card>
        <h1 className="text-2xl font-bold text-ss-text">Preferences</h1>
        <p className="mt-2 text-sm text-ss-muted">
          These choices are for client accounts. Admin sign-in alerts are on the <Link className="text-brand hover:underline" href="/admin">Admin page</Link>.
        </p>
      </Card>
    );
  }

  const left = unchosenCount(user);

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-ss-text">Your preferences</h1>
        <p className="mt-1 text-sm text-ss-muted">
          Three separate choices. Each is saved on its own, and you can change any of them at any time.
          Until you choose, we do not tag you to employers or send you alerts.
        </p>
        {left > 0 ? (
          <p className="mt-2 text-sm font-semibold text-ss-text" role="status">
            {left} of 3 still to choose. The reminder at the top of the site goes away once all three are chosen.
          </p>
        ) : (
          <p className="mt-2 text-sm font-semibold text-brand-dark" role="status">All three are chosen. Thank you.</p>
        )}
      </div>
      {err && <Alert kind="error">{err}</Alert>}
      {msg && <Alert kind="success">{msg}</Alert>}

      <Card>
        <fieldset>
          <legend className="flex flex-wrap items-center gap-2 text-lg font-semibold text-ss-text">
            Tagging by an administrator
            <StatusPill chosen={user?.tagging_state === "yes" || user?.tagging_state === "no"}>
              {yesNoLabel(user?.tagging_state)}
            </StatusPill>
          </legend>
          <p className="mt-1 text-sm text-ss-muted">
            May an administrator tag you to employers, that is, put you forward for posts that suit you?
            If you say no, or have not chosen, nobody can tag you.
          </p>
          <div className="mt-3 flex gap-5 text-sm text-ss-text">
            <label className="flex min-h-11 items-center gap-2">
              <input type="radio" name="tagging" checked={tagging === true} onChange={() => setTagging(true)} />
              Yes, they may
            </label>
            <label className="flex min-h-11 items-center gap-2">
              <input type="radio" name="tagging" checked={tagging === false} onChange={() => setTagging(false)} />
              No
            </label>
          </div>
          <div className="mt-3">
          <Button
            onClick={() => save("allow_tagging", tagging === true, "Your tagging choice is saved.")}
            disabled={tagging === null || busy !== null}
            loading={busy === "allow_tagging"}
          >
            Save tagging choice
          </Button>
          </div>
        </fieldset>
      </Card>

      <Card>
        <fieldset>
          <legend className="flex flex-wrap items-center gap-2 text-lg font-semibold text-ss-text">
            Preferred post
            <StatusPill chosen={user?.preferred_post_state === "chosen"}>
              {postTypeLabel(user?.preferred_post_state === "chosen" ? user?.preferred_post_type : null)}
            </StatusPill>
          </legend>
          <p className="mt-1 text-sm text-ss-muted">
            What kind of post would you like to be considered for? This is the type of role, not a job title.
            Choose &ldquo;Don&apos;t consider me&rdquo; if you would rather not be considered right now.
          </p>
          <div className="mt-3 grid gap-1 text-sm text-ss-text sm:grid-cols-2">
            {POST_TYPES.map((p) => (
              <label key={p.value} className="flex min-h-11 items-center gap-2">
                <input
                  type="radio"
                  name="post"
                  value={p.value}
                  checked={post === p.value}
                  onChange={() => setPost(p.value)}
                />
                {p.label}
              </label>
            ))}
          </div>
          <div className="mt-3">
          <Button
            onClick={() => save("preferred_post_type", post, "Your preferred post is saved.")}
            disabled={!post || busy !== null}
            loading={busy === "preferred_post_type"}
          >
            Save preferred post
          </Button>
          </div>
        </fieldset>
      </Card>

      <Card>
        <fieldset>
          <legend className="flex flex-wrap items-center gap-2 text-lg font-semibold text-ss-text">
            Alerts
            <StatusPill chosen={user?.alerts_state === "yes" || user?.alerts_state === "no"}>
              {yesNoLabel(user?.alerts_state)}
            </StatusPill>
          </legend>
          <p className="mt-1 text-sm text-ss-muted">
            May an administrator email you about a post that fits a role you named? This is off unless you say yes.
            The site does not score you against vacancies. You can switch this off here.
          </p>
          <div className="mt-3 flex gap-5 text-sm text-ss-text">
            <label className="flex min-h-11 items-center gap-2">
              <input type="radio" name="alerts" checked={alerts === true} onChange={() => setAlerts(true)} />
              Yes, send alerts
            </label>
            <label className="flex min-h-11 items-center gap-2">
              <input type="radio" name="alerts" checked={alerts === false} onChange={() => setAlerts(false)} />
              No
            </label>
          </div>
          <div className="mt-3">
          <Button
            onClick={() => save("notify_opportunity_alerts", alerts === true, "Your alerts choice is saved.")}
            disabled={alerts === null || busy !== null}
            loading={busy === "notify_opportunity_alerts"}
          >
            Save alerts choice
          </Button>
          </div>
        </fieldset>
      </Card>

      <p className="text-xs text-ss-muted">
        Why we ask: the Protection of Personal Information Act (POPIA) says we must have your permission before
        we use your information in these ways. Read the <Link className="text-brand hover:underline" href="/privacy">Privacy Policy</Link>.
        To remove your account altogether, use the <Link className="text-brand hover:underline" href="/security">Security page</Link>.
      </p>
    </div>
  );
}

export default function PreferencesPage() {
  return (
    <Guard>
      <PreferencesInner />
    </Guard>
  );
}
