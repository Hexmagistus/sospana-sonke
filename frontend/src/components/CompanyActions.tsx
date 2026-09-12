"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Button, Textarea } from "@/components/ui";
import { isShortlisted, toggleShortlist } from "@/lib/shortlist";
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

const NEW_WINDOW_MS = 1000 * 60 * 60 * 24 * 30;

/** "Last verified" / "Updated recently" / "Recently added" badges — honest,
 * not guessed: sourced directly from the URL tester / scan run (last_checked),
 * the page-hash checker (content_changed_at), and the row's own created_at.
 * See app/services/link_check_service.py. */
export function VerifiedBadge({ company }: { company: Company }) {
  const verified = timeAgo(company.last_checked);
  const updated = timeAgo(company.content_changed_at);
  const recentlyUpdated =
    !!company.content_changed_at &&
    Date.now() - new Date(company.content_changed_at).getTime() < 1000 * 60 * 60 * 24 * 14;
  const isNew =
    !!company.created_at && Date.now() - new Date(company.created_at).getTime() < NEW_WINDOW_MS;

  return (
    <span className="flex flex-wrap items-center gap-1.5">
      {isNew && (
        <span className="rounded-full bg-gold/20 px-2 py-0.5 text-[11px] font-semibold text-[#a9791a]">
          ✨ Recently added
        </span>
      )}
      {recentlyUpdated && (
        <span className="rounded-full bg-brand/10 px-2 py-0.5 text-[11px] font-semibold text-brand-dark">
          🔄 Updated {updated}
        </span>
      )}
      <span className="text-[11px] text-gray-400">
        {verified ? `Last verified ${verified}` : "Not yet verified"}
      </span>
    </span>
  );
}

/** "Popular this week" badge — driven by real notify-me subscription counts
 * (see watch_service.trending_company_ids), the only honest popularity signal
 * available without share/click tracking. The caller decides who qualifies. */
export function TrendingBadge() {
  return (
    <span className="rounded-full bg-coral/10 px-2 py-0.5 text-[11px] font-semibold text-coral">
      🔥 Popular this week
    </span>
  );
}

/** A star toggle backed by a per-browser localStorage shortlist (see
 * lib/shortlist.ts) — no account/server state, so it works the same whether
 * or not notify-me subscriptions are also in play. */
export function ShortlistStar({ companyId }: { companyId: string }) {
  const [on, setOn] = useState(false);

  useEffect(() => {
    setOn(isShortlisted(companyId));
  }, [companyId]);

  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        setOn(toggleShortlist(companyId));
      }}
      aria-label={on ? "Remove from shortlist" : "Add to shortlist"}
      aria-pressed={on}
      title={on ? "In your shortlist" : "Add to shortlist"}
      className={`rounded-full p-1 text-xl leading-none transition ${
        on ? "text-gold drop-shadow-sm" : "text-gray-300 hover:text-gray-400"
      }`}
    >
      {on ? "★" : "☆"}
    </button>
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
  const [celebrate, setCelebrate] = useState(false);

  function toggle(which: "notify" | "report") {
    setOpen((cur) => (cur === which ? null : which));
    setMsg("");
  }

  // A small checkmark/confetti flourish on success, not on error -- gone on
  // its own after a moment so it doesn't linger and clutter the card.
  function flashSuccess() {
    setCelebrate(true);
    window.setTimeout(() => setCelebrate(false), 1700);
  }

  async function subscribe() {
    setBusy(true);
    setMsg("");
    try {
      await api.post("/watches", { company_id: company.id });
      setMsg("Done — you'll get an email if this page changes.");
      setOpen(null);
      flashSuccess();
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
      flashSuccess();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Couldn't send the report — try again.");
    } finally {
      setBusy(false);
    }
  }

  async function share() {
    const url = `${window.location.origin}${shareBasePath}?company=${company.id}`;
    const text = `${company.company_name} — careers page on Sospana Sonke`;

    // Prefer the device's own share sheet (WhatsApp, Gmail, Messages, etc.) —
    // this is what people actually expect "Share" to do on a phone. Typed
    // loosely (not every TS/DOM lib version ships ShareData yet) rather than
    // assuming it's declared. Falls back to a plain clipboard copy where the
    // Web Share API isn't available (most desktop browsers).
    const nav = typeof navigator !== "undefined"
      ? (navigator as Navigator & { share?: (data: { title?: string; text?: string; url?: string }) => Promise<void> })
      : undefined;
    if (nav?.share) {
      try {
        await nav.share({ title: company.company_name, text, url });
        return;
      } catch (err) {
        // The user cancelling the share sheet isn't an error worth reporting.
        if (err instanceof Error && err.name === "AbortError") return;
        // Any other failure (unsupported combination, permissions, …) falls
        // through to the clipboard fallback below.
      }
    }

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

      {msg && (
        <p className="mt-1.5 flex items-center gap-1.5 text-xs text-brand-dark">
          {celebrate && <span className="animate-bounce text-sm" aria-hidden="true">🎉</span>}
          {msg}
        </p>
      )}
    </div>
  );
}
