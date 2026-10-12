"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui";

type Day = {
  day: string;
  searches: number;
  searches_with_results: number;
  searches_empty: number;
  searches_not_enough_data: number;
  clicks: number;
};

type Target = {
  target_kind: string;
  target_id: string;
  label: string;
  clicks: number;
};

type Scorecard = {
  window_days: number;
  retention_days: number;
  counted_on: string;
  searches: number;
  searches_with_results: number;
  searches_empty: number;
  searches_not_enough_data: number;
  search_success_rate: number | null;
  not_enough_data_rate: number | null;
  clicks: number;
  click_through_rate: number | null;
  results_returned: number;
  results_with_source: number;
  source_link_rate: number | null;
  definitions: Record<string, string>;
  by_day: Day[];
  clicks_by_target: Target[];
};

function percent(rate: number | null): string {
  if (rate === null) return "Not measured";
  return `${(rate * 100).toFixed(1)}%`;
}

export default function UsageScorecard() {
  const [card, setCard] = useState<Scorecard | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get<Scorecard>("/intelligence/admin/scorecard?days=7").then(setCard).catch((e) => setErr(e.message));
  }, []);

  return (
    <Card>
      <h2 className="mb-1 font-semibold text-ss-text">Search and click counts</h2>
      <p className="mb-3 text-sm text-ss-muted">
        Anonymous daily totals for the last 7 days. No question text, no account, and no IP address.
        Days before this release were not counted. Totals older than 90 days are deleted.
      </p>
      {err ? <p className="text-sm text-ss-text">{err}</p> : null}
      {!card && !err ? <p className="text-sm text-ss-muted">Loading the totals.</p> : null}
      {card ? (
        <>
          <p className="mb-3 text-sm text-ss-muted">Counted on {card.counted_on}. Kept for {card.retention_days} days.</p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="rounded-xl border border-ss-border p-3">
              <p className="text-sm text-ss-muted">Search success</p>
              <p className="text-xl font-bold text-ss-text">{percent(card.search_success_rate)}</p>
              <p className="mt-1 text-sm text-ss-text">
                {card.searches_with_results.toLocaleString("en-ZA")} of {card.searches.toLocaleString("en-ZA")} searches returned a result
              </p>
              <p className="mt-1 text-sm text-ss-muted">{card.definitions.search_success_rate}</p>
            </div>
            <div className="rounded-xl border border-ss-border p-3">
              <p className="text-sm text-ss-muted">Not enough data</p>
              <p className="text-xl font-bold text-ss-text">{percent(card.not_enough_data_rate)}</p>
              <p className="mt-1 text-sm text-ss-text">
                {card.searches_not_enough_data.toLocaleString("en-ZA")} of {card.searches.toLocaleString("en-ZA")} searches
              </p>
              <p className="mt-1 text-sm text-ss-muted">{card.definitions.not_enough_data_rate}</p>
            </div>
            <div className="rounded-xl border border-ss-border p-3">
              <p className="text-sm text-ss-muted">Click-through</p>
              <p className="text-xl font-bold text-ss-text">{percent(card.click_through_rate)}</p>
              <p className="mt-1 text-sm text-ss-text">
                {card.clicks.toLocaleString("en-ZA")} clicks on {card.searches_with_results.toLocaleString("en-ZA")} searches with results
              </p>
              <p className="mt-1 text-sm text-ss-muted">{card.definitions.click_through_rate}</p>
            </div>
            <div className="rounded-xl border border-ss-border p-3">
              <p className="text-sm text-ss-muted">Results with a source link</p>
              <p className="text-xl font-bold text-ss-text">{percent(card.source_link_rate)}</p>
              <p className="mt-1 text-sm text-ss-text">
                {card.results_with_source.toLocaleString("en-ZA")} of {card.results_returned.toLocaleString("en-ZA")} returned cards
              </p>
              <p className="mt-1 text-sm text-ss-muted">{card.definitions.source_link_rate}</p>
            </div>
          </div>
          <p className="mt-3 text-sm text-ss-text">
            Empty searches in this window: {card.searches_empty.toLocaleString("en-ZA")}.
          </p>
          {card.clicks_by_target.length > 0 ? (
            <ul className="mt-3 space-y-1 text-sm text-ss-text">
              {card.clicks_by_target.map((row) => (
                <li key={`${row.target_kind}-${row.target_id}`}>
                  {row.label}: {row.clicks.toLocaleString("en-ZA")} {row.clicks === 1 ? "click" : "clicks"}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-ss-muted">No outbound clicks in this window.</p>
          )}
        </>
      ) : null}
    </Card>
  );
}
