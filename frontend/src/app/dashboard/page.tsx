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
        <Stat label="Vacancies found" value={d.vacancies_open} />
        <Stat label="Strong matches" value={d.strong_matches} hint={`${d.total_matches} total`} />
        <Stat label="Applications submitted" value={d.applications_submitted} />
        <Stat label="Awaiting your action" value={d.applications_awaiting_action} />
        <Stat label="Tailored CVs" value={d.cvs_generated} />
        <Stat label="Cover letters" value={d.cover_letters_generated} />
        <Stat label="Interviews" value={d.interviews} />
        <Stat label="Offers" value={d.offers} />
      </div>

      <Card>
        <div className="flex flex-wrap gap-3">
          <Link href="/matches"><Button variant="ghost">View matches</Button></Link>
          <Link href="/cv"><Button variant="ghost">Manage CV</Button></Link>
          <Link href="/applications"><Button variant="ghost">Track applications</Button></Link>
          <Link href="/profile"><Button variant="ghost">Edit profile</Button></Link>
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
