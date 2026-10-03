"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui";
import { CompanyActionsRow, OpenVacancyCount } from "@/components/CompanyActions";
import { COUNTRY_FLAGS } from "@/lib/countryFlags";
import type { Company } from "@/lib/types";

/** A quick-look modal opened by clicking a directory card, so browsing the
 * list doesn't mean leaving the site on every click -- the same notify/share/
 * report actions are all still right here. */
export function CompanyPreviewModal({
  company,
  shareBasePath,
  onClose,
}: {
  company: Company;
  shareBasePath: string;
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-navy/40 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`${company.company_name} preview`}
        className="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-2xl bg-ss-surface p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-lg font-bold text-ss-text">{company.company_name}</div>
            {company.country && (
              <div className="mt-0.5 text-sm text-ss-muted">
                {COUNTRY_FLAGS[company.country] || "🌍"} {company.country}
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded-full p-1.5 text-ss-muted transition hover:bg-ss-primary-soft hover:text-ss-muted"
          >
            ✕
          </button>
        </div>

        <div className="mt-3">
          <OpenVacancyCount company={company} />
        </div>
        {company.notes && <p className="mt-2 text-sm text-ss-muted">{company.notes}</p>}

        <div className="mt-4">
          {company.careers_url ? (
            <a href={company.careers_url} target="_blank" rel="noopener noreferrer">
              <Button>View jobs →</Button>
            </a>
          ) : (
            <span className="text-xs text-ss-muted">No careers page yet</span>
          )}
        </div>

        <CompanyActionsRow company={company} shareBasePath={shareBasePath} />
      </div>
    </div>
  );
}
