"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Button, Textarea } from "@/components/ui";
import type { Company } from "@/lib/types";

function timeAgo(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return null;
  const days = Math.floor((Date.now() - then) / 86400000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} month${months === 1 ? "" : "s"} ago`;
  const years = Math.floor(months / 12);
  return `${years} year${years === 1 ? "" : "s"} ago`;
}

/** "Last verified" / "Updated recently" badges — honest, not guessed: sourced
 * directly from the URL tester / scan run (last_checked) and the page-hash
 * checker (content_changed_at). See app/services/link_check_service.py. */
export function VerifiedBadge({ company }: { company: Company }) {
  const verified = timeAgo(company.last_checked);
  const updated = timeAgo(company.content_changed_at);
  const recentlyUpdated =
    !!company.content_changed_at &&
    Date.now() - new Date(company.content_changed_at).getTime() < 1000 * 60 * 60 * 24 * 14;

  return (
    <span className="flex flex-wrap items-center gap-1.5">
      {recentlyUpdated && (
        <span className="rounded-full bg-brand/10 px-2 py-0.5 text-[11px] font-semibold text-brand-dark">
          ✨ Updated {updated}
        </span>
      )}
      <span className="text-[11px] text-gray-400">
        {verified ? `Last verified ${verified}` : "Not yet verified"}
      </span>
    </span>
  );
}

/** Notify-me / Report-link / Share row — shared by the Companies and
 * Universities directories so every listed employer gets the same feedback
 * loop, whatever page it's browsed from. */
export function CompanyActionsRow({ company, shareBasePath }: { company: Company; shareBasePath: string }) {
  const [open, setOpen] = useState<"notify" | "report" | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  function toggle(which: "notify" | "report") {
    setOpen((cur) => (cur === which ? null : which));
    setMsg("");
  }

  async function subscribe() {
    setBusy(true);
    setMsg("");
    try {
      await api.post("/watches", { company_id: company.id });
      setMsg("Done — you'll get an email if this page changes.");
      setOpen(null);
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Couldn't subscribe — try again.");
    } finally {
      setBusy(false);
    }
  }

  async function report() {
    if (reason.trim().length < 3) {
      setMsg("Say a little about what's wrong with the link.");
      return;
    }
    setBusy(true);
    setMsg("");
    try {
      await api.post(`/companies/${company.id}/report-link`, { reason });
      setMsg("Thanks — flagged for review.");
      setOpen(null);
      setReason("");
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Couldn't send the report — try again.");
    } finally {
      setBusy(false);
    }
  }

  function share() {
    const url = `${window.location.origin}${shareBasePath}?company=${company.id}`;
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(url).then(
        () => setMsg("Link copied to your clipboard."),
        () => setMsg(url),
      );
    } else {
      setMsg(url);
    }
  }

  return (
    <div className="mt-3 border-t border-gray-100 pt-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <VerifiedBadge company={company} />
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => toggle("notify")}
            className="rounded-md bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 transition hover:bg-gray-200"
          >
            🔔 Notify me
          </button>
          <button
            onClick={share}
            className="rounded-md bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 transition hover:bg-gray-200"
          >
            🔗 Share
          </button>
          <button
            onClick={() => toggle("report")}
            className="rounded-md bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 transition hover:bg-gray-200"
          >
            ⚠️ Report link
          </button>
        </div>
      </div>

      {open === "notify" && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <p className="flex-1 text-xs text-gray-500">Email me when this careers page changes.</p>
          <Button size="sm" loading={busy} onClick={subscribe}>Notify me</Button>
        </div>
      )}

      {open === "report" && (
        <div className="mt-2 space-y-2">
          <Textarea
            rows={2}
            placeholder="What's wrong with this link? (broken, wrong company, redirects elsewhere…)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <Button size="sm" loading={busy} onClick={report}>Send report</Button>
        </div>
      )}

      {msg && <p className="mt-1.5 text-xs text-brand-dark">{msg}</p>}
    </div>
  );
}
