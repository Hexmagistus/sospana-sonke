"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { Banner } from "@/components/Banner";
import { Alert, Card, Skeleton, Stat, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Dashboard } from "@/lib/types";

function DashboardInner() {
  const { user } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get<Dashboard>("/dashboard").then(setData).catch((e) => setErr(e.message));
  }, []);

  const firstName = user?.first_name || "there";

  return (
    <div className="space-y-6">
      <Banner
        variant="dashboard"
        eyebrow="My Opportunity Centre"
        title={`Welcome back, ${firstName} 👋`}
        subtitle={
          data
            ? `${data.vacancies_open.toLocaleString()} open vacancies are being matched against your profile right now.`
            : "Here's where things stand across your matches, CVs and applications."
        }
      >
        {data && (
          <div className="flex flex-wrap items-center gap-4">
            <StatusBadge tone="live" pulse>Live matching</StatusBadge>
            <StatusBadge tone="verified">Direct-to-employer sources</StatusBadge>
          </div>
        )}
      </Banner>

      {err && <Alert kind="error">{err}</Alert>}

      {data?.profile_nudge && (
        <Alert kind="info">
          <span>{data.profile_nudge} </span>
          <Link href="/profile" className="font-semibold underline underline-offset-2">
            Complete your profile →
          </Link>
        </Alert>
      )}

      {!data && !err && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      )}

      {data && (
        <>
          <div>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ss-muted">
              Your matches
            </h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              <Stat label="Open vacancies" value={data.vacancies_open} accent="sky" href="/companies" />
              <Stat label="Total matches" value={data.total_matches} accent="teal" href="/matches" />
              <Stat
                label="Strong matches"
                value={data.strong_matches}
                accent="gold"
                hint="Bands: Strong / Good"
                href="/matches"
              />
              <Stat
                label="Worth applying to"
                value={data.apply_matches}
                accent="coral"
                hint="Recommended decision: Apply"
                href="/matches"
              />
            </div>
          </div>

          <div>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ss-muted">
              CV studio
            </h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              <Stat label="CVs generated" value={data.cvs_generated} accent="purple" href="/master-cv" />
              <Stat
                label="Cover letters generated"
                value={data.cover_letters_generated}
                accent="navy"
                href="/tailor"
              />
            </div>
          </div>

          <div>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ss-muted">
              Application pipeline
            </h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              <Stat
                label="Total applications"
                value={data.applications_total}
                accent="teal"
                href="/tailor/applications"
              />
              <Stat
                label="Awaiting action"
                value={data.applications_awaiting_action}
                accent="gold"
                href="/tailor/applications"
              />
              <Stat label="Interviews" value={data.interviews} accent="coral" href="/tailor/applications" />
              <Stat label="Offers" value={data.offers} accent="purple" href="/tailor/applications" />
            </div>
          </div>

          <Card className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm text-ss-muted">
              Sospana Sonke is free forever — every feature above is unlocked, no subscription
              needed, now or later.
            </p>
          </Card>
        </>
      )}
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
