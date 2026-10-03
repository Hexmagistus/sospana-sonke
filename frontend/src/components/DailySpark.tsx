"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { SITE_URL } from "@/lib/seo";
import {
  addDays, attribution, pickSpark, prettyDate, sastDateString, shareText, type Spark,
} from "@/lib/dailySpark";

interface SparkStatus {
  today: string;
  opened_today: boolean;
  current_streak: number;
  longest_streak: number;
  total_opens: number;
}

async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    /* fall through to the textarea fallback */
  }
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}

function SparkBody({ spark, compact = false }: { spark: Spark; compact?: boolean }) {
  const { joke, wisdom } = spark;
  return (
    <div className={compact ? "space-y-3" : "grid gap-4 md:grid-cols-2"}>
      <section aria-label="Joke of the day" className="rounded-xl border border-ss-border bg-ss-surface/70 p-4">
        <h3 className="ss-hud-tag text-xs font-semibold text-ss-tech">Joke of the day</h3>
        <p className="mt-2 text-step-0 leading-relaxed text-ss-text">{joke.text}</p>
      </section>
      <section aria-label="Wisdom of the day" className="rounded-xl border border-ss-border bg-ss-surface/70 p-4">
        <h3 className="ss-hud-tag text-xs font-semibold text-ss-tech">Wisdom of the day</h3>
        <figure className="mt-2">
          {wisdom.native && (
            <p lang="und" className="mb-1 font-display text-step-1 font-semibold italic text-ss-primary">
              {wisdom.native}
            </p>
          )}
          <blockquote className="text-step-0 leading-relaxed text-ss-text">“{wisdom.text}”</blockquote>
          <figcaption className="mt-2 text-sm text-ss-muted">— {attribution(wisdom)}</figcaption>
        </figure>
      </section>
    </div>
  );
}

/** Members' Daily Spark: one joke and one piece of wisdom a day, revealed on request.
 * Opening it records only today's date so a streak can be shown. No reminders,
 * no emails and no notifications are involved; coming back is always optional. */
export default function DailySpark() {
  const [today, setToday] = useState<string>(() => sastDateString());
  const [revealed, setRevealed] = useState(false);
  const [status, setStatus] = useState<SparkStatus | null>(null);
  const [note, setNote] = useState("");
  const statusLoaded = useRef(false);

  const spark = pickSpark(today);
  const yesterday = pickSpark(addDays(today, -1));

  const loadStatus = useCallback(() => {
    api.get<SparkStatus>("/spark/status")
      .then((s) => {
        setStatus(s);
        if (s.opened_today) setRevealed(true);
        statusLoaded.current = true;
      })
      .catch(() => { /* streak is a bonus; the spark itself works offline */ });
  }, []);

  useEffect(() => { loadStatus(); }, [loadStatus]);

  // If the page stays open past midnight (South Africa time), move on to the new day.
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState !== "visible") return;
      const now = sastDateString();
      setToday((prev) => {
        if (prev !== now) { setRevealed(false); setNote(""); loadStatus(); }
        return now;
      });
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [loadStatus]);

  const reveal = () => {
    setRevealed(true); // show the spark straight away; the streak is recorded in the background
    api.post<SparkStatus>("/spark/open")
      .then(setStatus)
      .catch(() => { /* offline or signed out: still enjoy today's spark */ });
  };

  const share = async () => {
    const ok = await copyToClipboard(shareText(spark, SITE_URL));
    setNote(ok ? "Copied. Paste it anywhere you like." : "Couldn’t copy automatically. Select the text and copy it.");
    window.setTimeout(() => setNote(""), 4000);
  };

  const streak = status?.opened_today ? status.current_streak : null;

  return (
    <section
      aria-labelledby="daily-spark-title"
      className="ss-card-neon rounded-2xl border border-white/50 bg-ss-glass p-5 shadow-[0_18px_50px_-28px_rgba(11,31,58,0.55)] backdrop-blur-xl dark:border-white/10"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="ss-hud-tag text-xs font-semibold text-ss-tech">{prettyDate(today)}</p>
          <h2 id="daily-spark-title" className="mt-1 font-display text-step-2 font-bold text-ss-text">
            Daily Spark ✨
          </h2>
        </div>
        {streak !== null && streak > 0 && (
          <span className="ss-chip" title="Days in a row you opened your Daily Spark">
            <span aria-hidden="true">✨</span>
            {streak === 1 ? "Day 1 of your Spark streak" : `${streak} days of Sparks in a row`}
          </span>
        )}
      </div>

      {!revealed ? (
        <div className="mt-4 flex flex-col items-start gap-3 rounded-xl border border-dashed border-ss-primary-border-soft bg-ss-primary-soft p-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-step-0 text-ss-text">
            Today’s joke and a little wisdom are ready whenever you are.
          </p>
          <button
            type="button"
            onClick={reveal}
            className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-br from-[#163e73] to-[#0b1f3a] px-4 py-2 text-sm font-semibold text-white shadow-[0_12px_28px_-14px_rgba(11,31,58,0.85)] ring-1 ring-[#f5b301]/45 transition-all duration-ss hover:brightness-110 active:scale-[0.98]"
          >
            <span aria-hidden="true">✨</span> Reveal today’s spark
          </button>
        </div>
      ) : (
        <div className="ss-reveal mt-4 space-y-4" aria-live="polite">
          <SparkBody spark={spark} />
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={share}
              className="inline-flex items-center gap-2 rounded-lg border border-ss-border bg-ss-glass px-3 py-1.5 text-sm font-medium text-ss-text shadow-sm transition-all duration-ss hover:border-ss-tech"
            >
              <span aria-hidden="true">📋</span> Copy to share
            </button>
            <span role="status" className="text-sm text-ss-muted">{note}</span>
          </div>
        </div>
      )}

      <details className="group mt-4 rounded-xl border border-ss-border bg-ss-surface/50 p-3">
        <summary className="cursor-pointer text-sm font-semibold text-ss-text">
          Yesterday’s spark
        </summary>
        <div className="mt-3">
          <SparkBody spark={yesterday} compact />
        </div>
      </details>

      <p className="mt-4 text-sm text-ss-muted">
        A fresh spark appears tomorrow, when the new day starts in South Africa. No rush: it will be here whenever you are.
      </p>
    </section>
  );
}
