"use client";

import { useEffect, useState } from "react";
import { Spinner } from "./ui";

// A little levity for what can otherwise be an anxious silent wait: our free
// hosting tier dozes off when nobody's around, so the first request after a
// quiet spell can take a minute or two. Every line is honest about the fact
// that the server is a bit slow, that we're actively working on it, and that
// keeping Sospana Sonke free for everyone is exactly why we're on the patient
// tier for now. Rotates so a longer wait doesn't just repeat the same line.
// Shared by Guard (the auth check on every guarded page) and any page-level
// fetch that can hit the same cold start (Companies, Universities, Coverage…).
const LOADING_JOKES = [
  "Our server is a little slow to wake up (we're working on it!) — that's the trade-off for keeping this 100% free for everyone. Worth it. 💛",
  "Fun fact: the server naps when it's quiet. We're fixing the speed — meanwhile, access stays free for all. Stretch your legs, we've got this.",
  "Loading at the speed of 'free'. Our servers are getting an upgrade soon; until then, thanks for your patience (and your good taste in job platforms).",
  "Still here! The server's a bit sluggish today — we're on it. Free forever beats fast-but-paywalled, right? Right. 😄",
  "Waking the server. It's not a morning person, and honestly neither are we. Speed upgrades are coming; free access is here to stay.",
  "This can take 1–2 minutes on a cold start. We know it's slow and we're improving it — all so nobody ever pays to look for work. Kettle time? ☕",
  "Good things (and budget servers kept free on purpose) take a moment. Faster days are coming — pinky promise.",
];

export function FunSpinner({ label }: { label?: string }) {
  const [joke, setJoke] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setJoke((j) => (j + 1) % LOADING_JOKES.length), 7000);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="p-8 text-center">
      <Spinner label={label} />
      <p className="mx-auto mt-3 max-w-sm text-xs leading-relaxed text-ss-muted">{LOADING_JOKES[joke]}</p>
      <p className="mx-auto mt-2 max-w-xs text-[11px] font-semibold uppercase tracking-wider text-ss-tech">
        ● Slow server, big heart · always free
      </p>
    </div>
  );
}
