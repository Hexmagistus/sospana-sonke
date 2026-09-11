"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Alert, Spinner, Badge } from "@/components/ui";
import type { MasterCv } from "@/lib/types";

function ConfirmedTag({ confirmed }: { confirmed?: boolean }) {
  return confirmed ? (
    <span className="ml-2 text-xs font-medium text-green-700">verified ✓</span>
  ) : (
    <span className="ml-2 text-xs font-medium text-gray-400">unconfirmed</span>
  );
}

function MasterCvInner() {
  const [cv, setCv] = useState<MasterCv | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get<MasterCv>("/profile/master-cv").then(setCv).catch((e) => setErr(e.message));
  }, []);

  if (err) return <Alert kind="error">{err}</Alert>;
  if (!cv) return <Spinner />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-navy">My Master CV</h1>
        <p className="text-gray-500">
          The complete, verified record every tailored CV is generated from. Nothing here is ever invented — it comes
          only from what you&apos;ve added to your <Link href="/profile" className="text-brand hover:underline">profile</Link>.
          Generating a tailored CV never changes this record.
        </p>
      </div>

      <Card>
        <h2 className="mb-2 font-semibold">{cv.full_name || "—"}</h2>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-500">
          {cv.email && <span>{cv.email}</span>}
          {cv.phone && <span>{cv.phone}</span>}
          {cv.current_occupation && <span>{cv.current_occupation}</span>}
          {cv.years_experience != null && <span>{cv.years_experience} years experience</span>}
        </div>
        {cv.industries && cv.industries.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {cv.industries.map((i) => <Badge key={i}>{i}</Badge>)}
          </div>
        )}
      </Card>

      <Card>
        <h2 className="mb-3 font-semibold">Skills</h2>
        {cv.skills_detailed && cv.skills_detailed.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {cv.skills_detailed.map((s, i) => (
              <span key={i} className="rounded-full bg-gray-100 px-3 py-1 text-sm">
                {s.name}<ConfirmedTag confirmed={s.confirmed_by_candidate} />
              </span>
            ))}
          </div>
        ) : cv.skills.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {cv.skills.map((s) => <span key={s} className="rounded-full bg-gray-100 px-3 py-1 text-sm">{s}</span>)}
          </div>
        ) : (
          <p className="text-sm text-gray-400">No skills added yet — add them on your profile.</p>
        )}
      </Card>

      <Card>
        <h2 className="mb-3 font-semibold">Work experience</h2>
        {cv.experience.length === 0 ? (
          <p className="text-sm text-gray-400">No experience added yet.</p>
        ) : (
          <div className="space-y-4">
            {cv.experience.map((e, i) => (
              <div key={i} className="border-b border-gray-100 pb-3 last:border-0 last:pb-0">
                <div className="flex flex-wrap items-baseline gap-x-2">
                  <span className="font-medium">{String(e.position || "")}</span>
                  <span className="text-gray-400">—</span>
                  <span>{String(e.employer || "")}</span>
                  <ConfirmedTag confirmed={e.confirmed_by_candidate} />
                </div>
                <div className="text-xs text-gray-500">
                  {String(e.start_date || "?")} – {e.is_current ? "Present" : String(e.end_date || "?")}
                </div>
                {e.responsibilities != null && String(e.responsibilities).trim() && (
                  <p className="mt-1 text-sm text-gray-700">{String(e.responsibilities)}</p>
                )}
                {e.achievements != null && String(e.achievements).trim() && (
                  <p className="mt-1 text-sm text-gray-700"><span className="font-medium">Achievements:</span> {String(e.achievements)}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <h2 className="mb-3 font-semibold">Education</h2>
        {cv.education.length === 0 ? (
          <p className="text-sm text-gray-400">No education added yet.</p>
        ) : (
          <div className="space-y-2">
            {cv.education.map((e, i) => (
              <div key={i} className="text-sm">
                <span className="font-medium">{String(e.qualification || "")}</span> — {String(e.institution || "")}
                <ConfirmedTag confirmed={e.confirmed_by_candidate as boolean | undefined} />
              </div>
            ))}
          </div>
        )}
      </Card>

      {cv.certifications.length > 0 && (
        <Card>
          <h2 className="mb-3 font-semibold">Certifications</h2>
          <div className="space-y-2">
            {cv.certifications.map((c, i) => (
              <div key={i} className="text-sm">
                {String(c.name || "")}
                <ConfirmedTag confirmed={c.confirmed_by_candidate as boolean | undefined} />
              </div>
            ))}
          </div>
        </Card>
      )}

      {cv.professional_memberships && cv.professional_memberships.length > 0 && (
        <Card>
          <h2 className="mb-3 font-semibold">Professional memberships</h2>
          <ul className="list-disc pl-5 text-sm">
            {cv.professional_memberships.map((m, i) => <li key={i}>{m}</li>)}
          </ul>
        </Card>
      )}

      {cv.languages.length > 0 && (
        <Card>
          <h2 className="mb-3 font-semibold">Languages</h2>
          <div className="flex flex-wrap gap-2">
            {cv.languages.map((l) => <span key={l} className="rounded-full bg-gray-100 px-3 py-1 text-sm">{l}</span>)}
          </div>
        </Card>
      )}

      <Card>
        <p className="text-sm text-gray-500">
          To add or correct anything here, go to your <Link href="/profile" className="text-brand hover:underline">profile</Link>.
          When you&apos;re ready to apply for a specific role, use{" "}
          <Link href="/tailor" className="text-brand hover:underline">Build my job-aligned CV</Link> to generate a version
          tailored to that job — this Master CV is never overwritten.
        </p>
      </Card>
    </div>
  );
}

export default function MasterCvPage() {
  return (
    <Guard>
      <MasterCvInner />
    </Guard>
  );
}
