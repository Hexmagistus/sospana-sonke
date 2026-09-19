"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Button, Badge, Alert, Spinner, EmptyState, ErrorState } from "@/components/ui";
import type { Application } from "@/lib/types";

const STATUS_LABEL: Record<string, string> = {
  AWAITING_APPROVAL: "Awaiting your approval",
  CANDIDATE_ACTION_REQUIRED: "Action needed from you",
  APPLICATION_PREPARED: "Prepared",
  SUBMITTED: "Submitted",
  APPLICATION_FAILED: "Submission failed",
  INTERVIEW: "Interview",
  REJECTED_BY_EMPLOYER: "Not selected",
  WITHDRAWN: "Withdrawn",
  OFFER: "Offer",
  CLOSED: "Closed",
};

function Row({ app }: { app: Application }) {
  const [busy, setBusy] = useState<"cv" | "cl" | null>(null);
  const [err, setErr] = useState("");

  async function downloadCv() {
    if (!app.cv_version_id) return;
    setBusy("cv"); setErr("");
    try {
      await api.download(`/cv-versions/${app.cv_version_id}/download?fmt=pdf`, "CV.pdf");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not download the CV.");
    } finally {
      setBusy(null);
    }
  }

  async function downloadCoverLetter() {
    if (!app.cover_letter_id) return;
    setBusy("cl"); setErr("");
    try {
      await api.download(`/cover-letters/${app.cover_letter_id}/download?fmt=pdf`, "CoverLetter.pdf");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not download the cover letter.");
    } finally {
      setBusy(null);
    }
  }

  const needsYou = app.status === "AWAITING_APPROVAL" || app.status === "CANDIDATE_ACTION_REQUIRED";

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link href={`/applications/${app.id}`} className="font-semibold text-ss-text hover:underline">
            {app.vacancy_title || "A role"}
          </Link>
          <div className="text-sm text-ss-muted">
            {app.company_name || "Company not specified"}
            {app.vacancy_location && <> · {app.vacancy_location}</>}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {app.match_score != null && (
            <span className="text-sm text-ss-muted">Match {Math.round(app.match_score)}%</span>
          )}
          <Badge>{STATUS_LABEL[app.status] || app.status}</Badge>
        </div>
      </div>

      {err && <div className="mt-3"><Alert kind="error">{err}</Alert></div>}

      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-ss-border pt-4">
        {needsYou && (
          <Link href={`/applications/${app.id}`}>
            <Button size="sm">Review &amp; act →</Button>
          </Link>
        )}
        {!needsYou && (
          <Link href={`/applications/${app.id}`}>
            <Button size="sm" variant="ghost">View details</Button>
          </Link>
        )}
        {app.cv_version_id && (
          <Button size="sm" variant="ghost" loading={busy === "cv"} onClick={downloadCv}>CV (PDF)</Button>
        )}
        {app.cover_letter_id && (
          <Button size="sm" variant="ghost" loading={busy === "cl"} onClick={downloadCoverLetter}>Cover letter (PDF)</Button>
        )}
      </div>
    </Card>
  );
}

function ApplicationsInner() {
  const [apps, setApps] = useState<Application[] | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get<Application[]>("/applications").then(setApps).catch((e) => setErr(e.message));
  }, []);

  const needingReview = (apps || []).filter(
    (a) => a.status === "AWAITING_APPROVAL" || a.status === "CANDIDATE_ACTION_REQUIRED"
  ).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-ss-text">My applications</h1>
          <p className="text-ss-muted">
            Every application your Career Agent has prepared or you&apos;ve started — nothing is ever sent
            without you reviewing and approving it first.
          </p>
        </div>
        <Link href="/agent"><Button variant="ghost">Find more matches</Button></Link>
      </div>

      {err && <ErrorState message="We couldn't load your applications right now." detail={err} />}

      {!apps && !err ? (
        <Spinner />
      ) : apps && apps.length === 0 ? (
        <EmptyState
          icon="🗂️"
          title="No applications yet"
          message="Once your Career Agent finds a strong match, it'll draft a tailored CV and cover letter and queue a ready-to-review application here."
          action={<Link href="/agent"><Button>Go to Career Agent</Button></Link>}
        />
      ) : apps ? (
        <>
          {needingReview > 0 && (
            <Alert kind="info">
              {needingReview} application{needingReview === 1 ? "" : "s"} {needingReview === 1 ? "is" : "are"} waiting on you.
            </Alert>
          )}
          <div className="space-y-3">
            {apps.map((a) => <Row key={a.id} app={a} />)}
          </div>
        </>
      ) : null}
    </div>
  );
}

export default function ApplicationsPage() {
  return (
    <Guard>
      <ApplicationsInner />
    </Guard>
  );
}
