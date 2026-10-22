"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, getToken } from "@/lib/api";

const KEY = "ss-recent-roles";

type Recent = { id: string; title: string; company: string };

function readRecent(): Recent[] {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(KEY) || "[]") as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((row): row is Recent => {
        if (!row || typeof row !== "object") return false;
        const item = row as Recent;
        return typeof item.id === "string" && typeof item.title === "string" && typeof item.company === "string";
      })
      .slice(0, 8);
  } catch {
    return [];
  }
}

/** Remembers a role on this device only. Nothing is sent to the server. */
export function RememberRole({ id, title, company }: Recent) {
  useEffect(() => {
    const next = [{ id, title, company }, ...readRecent().filter((row) => row.id !== id)].slice(0, 8);
    try {
      window.localStorage.setItem(KEY, JSON.stringify(next));
    } catch {
      /* private mode: the page still works */
    }
  }, [id, title, company]);
  return null;
}

export function RecentRoles() {
  const [rows, setRows] = useState<Recent[]>([]);
  useEffect(() => setRows(readRecent()), []);
  if (rows.length === 0) return null;
  return (
    <section aria-label="Recently viewed" className="ss-card">
      <h2 className="text-lg font-bold text-ss-text">Recently viewed on this device</h2>
      <ul className="mt-2 space-y-1 text-sm">
        {rows.map((row) => (
          <li key={row.id}>
            <Link href={`/jobs/${row.id}`} className="font-semibold text-[#067589] underline">{row.title}</Link>
            <span className="text-ss-muted"> · {row.company}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function SavedRoles() {
  const [rows, setRows] = useState<Array<{ id: string; title: string; company_name: string; is_open: boolean }>>([]);
  useEffect(() => {
    if (!getToken()) return;
    api.get<Array<{ id: string; title: string; company_name: string; is_open: boolean }>>("/saved-opportunities")
      .then((data) => setRows(Array.isArray(data) ? data : []))
      .catch(() => setRows([]));
  }, []);
  if (rows.length === 0) return null;
  return (
    <section aria-label="Saved roles" className="ss-card">
      <h2 className="text-lg font-bold text-ss-text">Saved on your account</h2>
      <ul className="mt-2 space-y-1 text-sm">
        {rows.map((row) => (
          <li key={row.id}>
            <Link href={`/jobs/${row.id}`} className="font-semibold text-[#067589] underline">{row.title}</Link>
            <span className="text-ss-muted"> · {row.company_name}{row.is_open ? "" : " · closed"}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function SaveRoleButton({ id }: { id: string }) {
  const [message, setMessage] = useState("");
  async function save() {
    if (!getToken()) {
      setMessage("Sign in to save this role on your account.");
      return;
    }
    try {
      await api.post("/saved-opportunities", { vacancy_id: id });
      setMessage("Saved to your account.");
    } catch {
      setMessage("Could not save that role. It may no longer be open.");
    }
  }
  return (
    <div className="mt-4">
      <button type="button" onClick={save} className="ss-intel-button min-h-11">
        Save this role
      </button>
      {message ? (
        <p role="status" className="mt-2 text-sm text-ss-text">
          {message}{" "}
          
        </p>
      ) : (
        <p className="mt-2 text-sm text-ss-muted">Saved roles stay on your account. Recently viewed stays on this device.</p>
      )}
    </div>
  );
}
