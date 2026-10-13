"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button, Field, Input, Select } from "@/components/ui";
import { sortCountries } from "@/lib/directoryFilters";

type AlertRow = {
  id: string;
  country: string | null;
  category: string | null;
  keyword: string | null;
  opportunity_type: string | null;
  active: boolean;
};

type MatchRow = {
  title: string;
  employer: string;
  country: string;
  url: string | null;
  last_seen: string | null;
};

type Preview = {
  email_sent: boolean;
  would_send: boolean;
  cadence: string;
  digest_eligible: boolean;
  would_email: MatchRow[];
  open_matches: MatchRow[];
};

const CATEGORIES: { value: string; label: string }[] = [
  { value: "", label: "Any category" },
  { value: "SOE", label: "State-owned" },
  { value: "MUNI", label: "Municipality" },
  { value: "DEPT", label: "Department" },
  { value: "PRIVATE", label: "Private" },
  { value: "NGO", label: "NGO" },
  { value: "UNI", label: "University" },
  { value: "COLLEGE", label: "College" },
  { value: "HOSPITAL", label: "Hospital" },
  { value: "SETA", label: "SETA" },
  { value: "JSE", label: "Listed" },
  { value: "SPORT", label: "Sports" },
  { value: "FED", label: "Federations" },
  { value: "MUSIC", label: "Music" },
];

const TYPES: { value: string; label: string }[] = [
  { value: "", label: "Any type" },
  { value: "job", label: "Job" },
  { value: "internship", label: "Internship" },
  { value: "learnership", label: "Learnership" },
  { value: "bursary", label: "Bursary" },
  { value: "graduate_programme", label: "Graduate programme" },
];

const SKIP_COUNTRIES = new Set(["International", "Africa"]);

function typeLabel(code: string | null): string {
  if (!code) return "Any type";
  return TYPES.find((row) => row.value === code)?.label || code;
}

function categoryLabel(code: string | null): string {
  if (!code) return "Any category";
  return CATEGORIES.find((row) => row.value === code)?.label || code;
}

function describe(row: AlertRow): string {
  return [row.country || "Any country", categoryLabel(row.category), typeLabel(row.opportunity_type), row.keyword || "Any keyword"].join(" · ");
}

const emptyForm = { country: "", category: "", keyword: "", opportunity_type: "" };

export default function RoleAlerts() {
  const [alerts, setAlerts] = useState<AlertRow[]>([]);
  const [countries, setCountries] = useState<string[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);

  async function load() {
    const rows = await api.get<AlertRow[]>("/alerts");
    setAlerts(rows);
  }

  useEffect(() => {
    let gone = false;
    load().catch(() => {
      if (!gone) setErr("Saved alerts could not be loaded.");
    });
    api.get<{ by_country?: Record<string, number> }>("/companies/stats")
      .then((stats) => {
        if (gone) return;
        const names = Object.keys(stats.by_country || {}).filter((name) => name && !SKIP_COUNTRIES.has(name));
        setCountries(sortCountries(names));
      })
      .catch(() => {
        if (!gone) setCountries([]);
      });
    return () => {
      gone = true;
    };
  }, []);

  function beginEdit(row: AlertRow) {
    setEditing(row.id);
    setPreview(null);
    setForm({
      country: row.country || "",
      category: row.category || "",
      keyword: row.keyword || "",
      opportunity_type: row.opportunity_type || "",
    });
    setErr("");
    setMsg("");
  }

  async function save() {
    setErr("");
    setMsg("");
    setBusy(true);
    const body = {
      country: form.country.trim() || null,
      category: form.category.trim() || null,
      keyword: form.keyword.trim() || null,
      opportunity_type: form.opportunity_type.trim() || null,
    };
    try {
      if (editing) {
        await api.put(`/alerts/${editing}`, body);
        setMsg("Alert updated. It is on, and the daily email will use it.");
      } else {
        await api.post("/alerts", body);
        setMsg("Alert saved. We email once a day, and only when a new stored role matches.");
      }
      setForm(emptyForm);
      setEditing(null);
      setPreview(null);
      await load();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "Could not save that alert");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    setErr("");
    setMsg("");
    setBusy(true);
    try {
      await api.del(`/alerts/${id}`);
      if (editing === id) {
        setEditing(null);
        setForm(emptyForm);
      }
      setPreview(null);
      setMsg("Alert deleted.");
      await load();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "Could not delete that alert");
    } finally {
      setBusy(false);
    }
  }

  async function runPreview() {
    setErr("");
    setMsg("");
    setBusy(true);
    try {
      const body = await api.get<Preview>("/alerts/preview");
      setPreview(body);
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "Could not preview alerts");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-2xl border border-ss-border bg-ss-surface p-4 shadow-sm sm:p-5" aria-labelledby="role-alerts-heading">
      <h2 id="role-alerts-heading" className="text-lg font-semibold text-ss-text">Daily role alerts</h2>
      <p className="mt-1 text-sm text-ss-muted">
        Save a country, a category, a keyword, an opportunity type, or any mix. Leave the type blank for any type, or save a type on its own. A match can be a job, an internship, a learnership, a bursary or a graduate programme. This is a separate choice from the administrator
        alerts above. We send one email a day, and only when a new stored role matches. Each role includes
        the employer&apos;s link and the date we last saw it. A day with no match stays quiet. The alert
        starts when you press Save this alert.
      </p>

      {err && <p className="mt-3 text-sm font-medium text-ss-danger" role="alert">{err}</p>}
      {msg && <p className="mt-3 text-sm font-medium text-brand-dark" role="status">{msg}</p>}

      <form
        className="mt-4 grid gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Country" hint="Optional">
            {countries.length > 0 ? (
              <Select
                aria-label="Country"
                value={form.country}
                onChange={(event) => setForm({ ...form, country: event.target.value })}
              >
                <option value="">Any country</option>
                {countries.map((name) => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </Select>
            ) : (
              <Input
                aria-label="Country"
                value={form.country}
                placeholder="South Africa"
                maxLength={60}
                onChange={(event) => setForm({ ...form, country: event.target.value })}
              />
            )}
          </Field>
          <Field label="Category" hint="Optional">
            <Select
              aria-label="Category"
              value={form.category}
              onChange={(event) => setForm({ ...form, category: event.target.value })}
            >
              {CATEGORIES.map((row) => (
                <option key={row.value || "any"} value={row.value}>{row.label}</option>
              ))}
            </Select>
          </Field>
          <Field label="Type" hint="Optional">
            <Select
              aria-label="Opportunity type"
              value={form.opportunity_type}
              onChange={(event) => setForm({ ...form, opportunity_type: event.target.value })}
            >
              {TYPES.map((row) => (
                <option key={row.value || "any-type"} value={row.value}>{row.label}</option>
              ))}
            </Select>
          </Field>
          <Field label="Keyword" hint="Optional">
            <Input
              aria-label="Keyword"
              value={form.keyword}
              placeholder="nurse"
              maxLength={80}
              onChange={(event) => setForm({ ...form, keyword: event.target.value })}
            />
          </Field>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={busy} loading={busy}>
            {editing ? "Save changes" : "Save this alert"}
          </Button>
          {editing && (
            <Button
              type="button"
              variant="ghost"
              disabled={busy}
              onClick={() => {
                setEditing(null);
                setForm(emptyForm);
              }}
            >
              Cancel edit
            </Button>
          )}
        </div>
      </form>

      <ul className="mt-4 space-y-2">
        {alerts.length === 0 && (
          <li className="text-sm text-ss-muted">No saved alerts yet.</li>
        )}
        {alerts.map((row) => (
          <li key={row.id} className="flex flex-col gap-2 rounded-xl border border-ss-border px-3 py-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-ss-text">
              {describe(row)}
              {row.active ? "" : " · paused"}
            </p>
            <div className="flex gap-2">
              <Button type="button" variant="secondary" className="min-h-11" disabled={busy} onClick={() => beginEdit(row)}>
                Edit
              </Button>
              <Button type="button" variant="ghost" className="min-h-11" disabled={busy} onClick={() => void remove(row.id)}>
                Delete
              </Button>
            </div>
          </li>
        ))}
      </ul>

      <div className="mt-4">
        <Button type="button" variant="secondary" disabled={busy || alerts.length === 0} onClick={() => void runPreview()}>
          Preview matching roles
        </Button>
        <p className="mt-1 text-xs text-ss-muted">Preview only. No email is sent.</p>
      </div>

      {preview && (
        <div className="mt-3 space-y-3 text-sm text-ss-text">
          <p>{preview.cadence} {preview.email_sent ? "" : "No email was sent."}</p>
          <div>
            <h3 className="font-semibold">Would be in today&apos;s email</h3>
            {preview.would_email.length === 0 ? (
              <p className="text-ss-muted">Nothing new in the last 24 hours matches.</p>
            ) : (
              <ul className="mt-1 space-y-1">
                {preview.would_email.map((row) => (
                  <MatchLine key={`${row.title}-${row.url}`} row={row} />
                ))}
              </ul>
            )}
          </div>
          <div>
            <h3 className="font-semibold">Open roles we currently hold</h3>
            <p className="text-ss-muted">These can be older than one day. They are not all emailed.</p>
            {preview.open_matches.length === 0 ? (
              <p className="text-ss-muted">No open stored role matches.</p>
            ) : (
              <ul className="mt-1 space-y-1">
                {preview.open_matches.map((row) => (
                  <MatchLine key={`${row.title}-${row.last_seen}-${row.url}`} row={row} />
                ))}
              </ul>
            )}
          </div>
          {!preview.digest_eligible && (
            <p className="text-ss-muted">Verify your email address before the morning digest can include this account.</p>
          )}
        </div>
      )}
    </section>
  );
}

function MatchLine({ row }: { row: MatchRow }) {
  return (
    <li>
      {row.title} at {row.employer}
      {row.country ? `, ${row.country}` : ""}
      {row.last_seen ? `, last seen ${row.last_seen}` : ""}
      {row.url ? (
        <>
          {" "}
          <a className="text-brand hover:underline" href={row.url} rel="noopener noreferrer" target="_blank">
            Source
          </a>
        </>
      ) : null}
    </li>
  );
}
