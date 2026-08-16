"use client";

import { useEffect, useState } from "react";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Field, Input, Button, Alert, Spinner, Badge } from "@/components/ui";

interface Child {
  id: string;
  confirmed_by_candidate: boolean;
  source: string;
  [k: string]: unknown;
}

function ProfileInner() {
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);
  const [skills, setSkills] = useState<Child[]>([]);
  const [education, setEducation] = useState<Child[]>([]);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  async function loadAll() {
    setProfile(await api.get("/profile"));
    setSkills(await api.get("/profile/skills"));
    setEducation(await api.get("/profile/education"));
  }
  useEffect(() => {
    loadAll().catch((e) => setErr(e.message));
  }, []);

  async function saveProfile(e: React.FormEvent) {
    e.preventDefault();
    setMsg(""); setErr("");
    const p = profile!;
    try {
      await api.put("/profile", {
        city: p.city || null,
        current_occupation: p.current_occupation || null,
        years_experience: p.years_experience ? Number(p.years_experience) : null,
        minimum_salary: p.minimum_salary ? Number(p.minimum_salary) : null,
        work_authorization: p.work_authorization || null,
        drivers_licence: p.drivers_licence || null,
        desired_occupations: strToList(p.desired_occupations),
        industries: strToList(p.industries),
        preferred_locations: strToList(p.preferred_locations),
      });
      setMsg("Profile saved.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Save failed");
    }
  }

  function strToList(v: unknown): string[] {
    if (Array.isArray(v)) return v as string[];
    if (typeof v === "string") return v.split(",").map((s) => s.trim()).filter(Boolean);
    return [];
  }
  function listToStr(v: unknown): string {
    return Array.isArray(v) ? (v as string[]).join(", ") : "";
  }
  function set(k: string, v: unknown) {
    setProfile((p) => ({ ...(p || {}), [k]: v }));
  }

  if (err && !profile) return <Alert kind="error">{err}</Alert>;
  if (!profile) return <Spinner />;
  const p = profile;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">My profile</h1>
      {msg && <Alert kind="success">{msg}</Alert>}
      {err && <Alert kind="error">{err}</Alert>}

      <Card>
        <form onSubmit={saveProfile} className="grid gap-4 md:grid-cols-2">
          <Field label="Current occupation">
            <Input value={(p.current_occupation as string) || ""} onChange={(e) => set("current_occupation", e.target.value)} />
          </Field>
          <Field label="City">
            <Input value={(p.city as string) || ""} onChange={(e) => set("city", e.target.value)} />
          </Field>
          <Field label="Years of experience">
            <Input type="number" value={(p.years_experience as number) ?? ""} onChange={(e) => set("years_experience", e.target.value)} />
          </Field>
          <Field label="Minimum monthly salary (ZAR)">
            <Input type="number" value={(p.minimum_salary as number) ?? ""} onChange={(e) => set("minimum_salary", e.target.value)} />
          </Field>
          <Field label="Work authorisation">
            <Input value={(p.work_authorization as string) || ""} onChange={(e) => set("work_authorization", e.target.value)} />
          </Field>
          <Field label="Driver's licence">
            <Input value={(p.drivers_licence as string) || ""} onChange={(e) => set("drivers_licence", e.target.value)} />
          </Field>
          <Field label="Desired occupations (comma-separated)">
            <Input value={listToStr(p.desired_occupations)} onChange={(e) => set("desired_occupations", e.target.value)} />
          </Field>
          <Field label="Industries (comma-separated)">
            <Input value={listToStr(p.industries)} onChange={(e) => set("industries", e.target.value)} />
          </Field>
          <Field label="Preferred locations (comma-separated)">
            <Input value={listToStr(p.preferred_locations)} onChange={(e) => set("preferred_locations", e.target.value)} />
          </Field>
          <div className="md:col-span-2">
            <Button type="submit">Save profile</Button>
          </div>
        </form>
      </Card>

      <ChildSection
        title="Skills"
        items={skills}
        fields={[{ key: "name", label: "Skill" }, { key: "category", label: "Category" }]}
        onAdd={async (v) => { await api.post("/profile/skills", v); setSkills(await api.get("/profile/skills")); }}
        onDelete={async (id) => { await api.del(`/profile/skills/${id}`); setSkills(await api.get("/profile/skills")); }}
        render={(i) => `${i.name}${i.category ? ` (${i.category})` : ""}`}
      />

      <ChildSection
        title="Education"
        items={education}
        fields={[{ key: "institution", label: "Institution" }, { key: "qualification", label: "Qualification" }, { key: "level", label: "Level" }]}
        onAdd={async (v) => { await api.post("/profile/education", v); setEducation(await api.get("/profile/education")); }}
        onDelete={async (id) => { await api.del(`/profile/education/${id}`); setEducation(await api.get("/profile/education")); }}
        render={(i) => `${i.qualification || ""} — ${i.institution}`}
      />
    </div>
  );
}

function ChildSection({
  title, items, fields, onAdd, onDelete, render,
}: {
  title: string;
  items: Child[];
  fields: { key: string; label: string }[];
  onAdd: (v: Record<string, string>) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  render: (i: Child) => string;
}) {
  const [form, setForm] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  return (
    <Card>
      <h2 className="mb-3 text-lg font-semibold">{title}</h2>
      <ul className="mb-4 space-y-2">
        {items.length === 0 && <li className="text-sm text-gray-400">Nothing yet.</li>}
        {items.map((i) => (
          <li key={i.id} className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2 text-sm">
            <span>
              {render(i)}{" "}
              {!i.confirmed_by_candidate && <Badge>from CV</Badge>}
            </span>
            <button onClick={() => onDelete(i.id)} className="text-xs text-red-500 hover:underline">
              Remove
            </button>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap items-end gap-2">
        {fields.map((f) => (
          <div key={f.key} className="flex-1 min-w-[8rem]">
            <Field label={f.label}>
              <Input value={form[f.key] || ""} onChange={(e) => setForm((s) => ({ ...s, [f.key]: e.target.value }))} />
            </Field>
          </div>
        ))}
        <Button
          variant="ghost"
          disabled={busy || !form[fields[0].key]}
          onClick={async () => {
            setBusy(true);
            try { await onAdd(form); setForm({}); } finally { setBusy(false); }
          }}
        >
          Add
        </Button>
      </div>
    </Card>
  );
}

export default function ProfilePage() {
  return (
    <Guard>
      <ProfileInner />
    </Guard>
  );
}
