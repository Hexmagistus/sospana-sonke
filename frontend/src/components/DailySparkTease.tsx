"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { pickSpark, sastDateString } from "@/lib/dailySpark";

/** Pre-login teaser for the Daily Spark: today's joke is public, today's wisdom
 * and the streak live inside a free account. Self-contained so the landing page only
 * needs a single <DailySparkTease /> line. */
export default function DailySparkTease() {
  // Computed after mount so the server-rendered HTML never disagrees with the visitor's date.
  const [joke, setJoke] = useState<string | null>(null);
  useEffect(() => { setJoke(pickSpark(sastDateString()).joke.text); }, []);

  return (
    <section aria-labelledby="spark-tease-title" className="mx-auto max-w-6xl px-4 py-10">
      <div className="ss-card-neon relative overflow-hidden rounded-[1.6rem] border-2 border-gold bg-gradient-to-br from-[#fffaf0] to-[#ffefc2] p-6 text-ss-text shadow-[0_18px_44px_-28px_rgba(11,36,71,0.5)] sm:p-8">
        <div className="grid gap-6 md:grid-cols-[1.2fr_1fr] md:items-center">
          <div>
            <p className="ss-hud-tag text-xs font-semibold text-ss-primary">New every day</p>
            <h2 id="spark-tease-title" className="mt-1 font-display text-step-3 font-extrabold">
              Daily Spark ✨
            </h2>
            <p className="mt-2 max-w-prose text-step-0 text-ss-text">
              A clean joke and a line of wisdom to start the job-hunt day, from African proverbs to Mandela, Maathai and Achebe. Free for members.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link
                href="/register"
                className="rounded-lg bg-[#f5b301] px-4 py-2 text-sm font-bold text-[#0b2447] shadow-md transition-all duration-ss hover:brightness-105"
              >
                Join free to reveal it
              </Link>
              <Link
                href="/login"
                className="rounded-lg px-4 py-2 text-sm font-semibold text-navy ring-2 ring-navy/60 transition-all duration-ss hover:bg-white"
              >
                I already have an account
              </Link>
            </div>
          </div>
          <div className="space-y-3">
            <div className="rounded-xl bg-ss-surface p-4 ring-1 ring-ss-border">
              <h3 className="ss-hud-tag text-xs font-semibold text-ss-primary">Today’s joke, on the house</h3>
              <p className="mt-2 min-h-[3.5rem] text-step-0 leading-relaxed" aria-live="polite">
                {joke ?? "…"}
              </p>
            </div>
            <div className="rounded-xl border border-dashed border-gold p-4 text-sm text-ss-text">
              Today’s wisdom is waiting inside. Members can also keep a gentle streak of the days they open it. No reminders, ever.
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
