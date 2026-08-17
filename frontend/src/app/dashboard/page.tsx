"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Stat, Card, Button, Alert, Spinner, Badge } from "@/components/ui";
import type { Dashboard } from "@/lib/types";

function DashboardInner() {
  const [d, setD] = useState<Dashboard | null>(null);
  const [err, setErr] = useState("");
  const [running, setRunning] = useState(false);

  async function load() {
    try {
      setD(await api.get<Dashboard>("/dashboard"));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load");
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function runMatching() {
    setRunning(true);
    setErr("");
    try {
      await api.post("/matches/run");
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Matching failed");
    } finally {
      setRunning(false);
    }
  }

  if (err) return <Alert kind="error">{err}</Alert>;
  if (!d) return <Spinner />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">
            Subscription: <Badge>{d.subscription_status}</Badge> · R{d.plan_amount_zar}/mo
          </span>
          <Button onClick={runMatching} disabled={running}>
            {running ? "Finding matches…" : "Find new matches"}
          </Button>
        </div>
      </div>

      {!d.has_access && (
        <Alert kind="error">
          Your subscription is inactive.{" "}
          <Link href="/subscription" className="font-medium underline">
            Subscribe to unlock matching and applications
          </Link>
          .
        </Alert>
      )}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Vacancies found" value={d.vacancies_open} accent="sky" />
        <Stat label="Strong matches" value={d.strong_matches} hint={`${d.total_matches} total`} accent="teal" />
        <Stat label="Applications submitted" value={d.applications_submitted} accent="purple" />
        <Stat label="Awaiting your action" value={d.applications_awaiting_action} accent="coral" />
        <Stat label="Tailored CVs" value={d.cvs_generated} accent="gold" />
        <Stat label="Cover letters" value={d.cover_letters_generated} accent="navy" />
        <Stat label="Interviews" value={d.interviews} accent="teal" />
        <Stat label="Offers" value={d.offers} accent="gold" />
      </div>

      <Card accent="gold">
        <div className="mb-3 text-sm font-semibold text-navy">Quick actions</div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Link href="/companies" className="group rounded-xl bg-gradient-to-br from-sky/10 to-sky/5 p-4 ring-1 ring-sky/20 transition hover:shadow-md">
            <div className="text-2xl">🔍</div>
            <div className="mt-2 font-semibold text-navy">Browse companies</div>
            <div className="text-xs text-gray-500">367+ SA employers</div>
          </Link>
          <Link href="/tailor" className="group rounded-xl bg-gradient-to-br from-purple/10 to-purple/5 p-4 ring-1 ring-purple/20 transition hover:shadow-md">
            <div className="text-2xl">✍️</div>
            <div className="mt-2 font-semibold text-navy">Tailor my CV</div>
            <div className="text-xs text-gray-500">CV + cover letter</div>
          </Link>
          <Link href="/applications" className="group rounded-xl bg-gradient-to-br from-coral/10 to-coral/5 p-4 ring-1 ring-coral/20 transition hover:shadow-md">
            <div className="text-2xl">📊</div>
            <div className="mt-2 font-semibold text-navy">Track applications</div>
            <div className="text-xs text-gray-500">Stay organised</div>
          </Link>
          <Link href="/profile" className="group rounded-xl bg-gradient-to-br from-brand/10 to-brand/5 p-4 ring-1 ring-brand/20 transition hover:shadow-md">
            <div className="text-2xl">👤</div>
            <div className="mt-2 font-semibold text-navy">Edit profile</div>
            <div className="text-xs text-gray-500">Keep it current</div>
          </Link>
        </div>
      </Card>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Guard>
      <DashboardInner />
    </Guard>
  );
}
