"use client";

import { useEffect, useRef, useState } from "react";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Alert, Spinner, Button, Badge, Input } from "@/components/ui";
import type { Company } from "@/lib/types";

function CompaniesInner() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    setCompanies(await api.get<Company[]>("/companies?limit=5000"));
  }
  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, []);

  async function importCsv() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setBusy(true); setErr(""); setMsg("");
    try {
      const r = await api.upload<{ created: number; updated: number; total_rows: number }>("/companies/import", file);
      setMsg(`Imported: ${r.created} new, ${r.updated} updated (of ${r.total_rows} rows).`);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Import failed");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function scan(id: string) {
    setErr(""); setMsg("");
    try {
      const reports = await api.post<{ status: string; created: number }[]>(`/companies/${id}/scan`);
      const r = reports[0];
      setMsg(`Scan finished: ${r?.status}${r ? `, ${r.created} vacancies found` : ""}.`);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Scan failed");
    }
  }

  const filtered = companies.filter((c) => c.company_name.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Company database</h1>
      {msg && <Alert kind="success">{msg}</Alert>}
      {err && <Alert kind="error">{err}</Alert>}

      <Card>
        <h2 className="mb-2 font-semibold">Import companies (CSV)</h2>
        <div className="flex items-center gap-3">
          <input ref={fileRef} type="file" accept=".csv" className="text-sm" />
          <Button onClick={importCsv} disabled={busy}>{busy ? "Importing…" : "Import"}</Button>
        </div>
      </Card>

      <Card>
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="font-semibold">Companies ({filtered.length})</h2>
          <Input placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} className="max-w-xs" />
        </div>
        {companies.length === 0 ? (
          <Spinner />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-gray-500">
                <tr>
                  <th className="py-2">Company</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Careers URL</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0, 200).map((c) => (
                  <tr key={c.id} className="border-t border-gray-100">
                    <td className="py-2 font-medium">{c.company_name} {c.jse_code && <span className="text-gray-400">({c.jse_code})</span>}</td>
                    <td><Badge>{c.source_type}</Badge></td>
                    <td className="text-gray-600">{c.scraping_status}</td>
                    <td className="max-w-[16rem] truncate text-gray-500">
                      {c.careers_url ? <a href={c.careers_url} target="_blank" rel="noreferrer" className="text-brand hover:underline">{c.careers_url}</a> : "—"}
                    </td>
                    <td className="text-right">
                      {c.careers_url && (
                        <button onClick={() => scan(c.id)} className="text-xs text-brand hover:underline">Scan now</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length > 200 && <p className="mt-2 text-xs text-gray-400">Showing first 200. Refine your search to see more.</p>}
          </div>
        )}
      </Card>
    </div>
  );
}

export default function CompaniesPage() {
  return (
    <Guard admin>
      <CompaniesInner />
    </Guard>
  );
}
