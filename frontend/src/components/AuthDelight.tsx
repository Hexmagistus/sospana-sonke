"use client";

import { useEffect, useState } from "react";

/** Local greetings. The English time-of-day stays put; the word beside it rotates. */
const GREETINGS = [
  { word: "Sawubona", note: "isiZulu · we see you" },
  { word: "Dumela", note: "Setswana · hello" },
  { word: "Molo", note: "isiXhosa · hello" },
  { word: "Howzit", note: "a South African hello" },
  { word: "Bonjour", note: "a francophone hello" },
  { word: "Olá", note: "a lusophone hello" },
];

function timeOfDay(hour: number): string {
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setReduced(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);
  return reduced;
}

export function GreetingLine() {
  const reduced = usePrefersReducedMotion();
  const [index, setIndex] = useState(0);
  const [hello, setHello] = useState("Hello");

  useEffect(() => {
    setHello(timeOfDay(new Date().getHours()));
    if (reduced) return;
    const id = window.setInterval(() => {
      setIndex((n) => (n + 1) % GREETINGS.length);
    }, 4200);
    return () => window.clearInterval(id);
  }, [reduced]);

  const greet = GREETINGS[index];
  return (
    <p className="mb-3 text-center text-sm text-blue-100" aria-live="polite">
      <span className="font-semibold text-white">{hello}</span>
      {" — "}
      <span className="font-semibold text-[#ffcf5a]">{greet.word}</span>
      <span className="mt-0.5 block text-xs text-blue-200">{greet.note}</span>
    </p>
  );
}

/** Geometric circuit mark. Covers its eyes while a password is being typed. */
export function CircuitMascot({
  coverEyes,
  celebrate,
}: {
  coverEyes: boolean;
  celebrate: boolean;
}) {
  return (
    <svg
      viewBox="0 0 72 72"
      className="h-16 w-16"
      role="img"
      aria-label={celebrate ? "Signed in" : coverEyes ? "Looking away from the password" : "Ready"}
    >
      <circle cx="36" cy="36" r="30" fill="#0b1f3a" stroke="#f5b301" strokeWidth="2" />
      <path d="M14 36h10M48 36h10M36 12v8M36 52v8" stroke="#f5b301" strokeWidth="1.4" strokeLinecap="round" opacity="0.85" />
      {coverEyes ? (
        <g>
          <path d="M20 32c6 6 12 6 16 0" fill="none" stroke="#f4f8ff" strokeWidth="2.4" strokeLinecap="round" />
          <path d="M36 32c6 6 12 6 16 0" fill="none" stroke="#f4f8ff" strokeWidth="2.4" strokeLinecap="round" />
          <path d="M18 28h16M38 28h16" stroke="#f5b301" strokeWidth="3" strokeLinecap="round" />
        </g>
      ) : (
        <g>
          <circle cx="27" cy="32" r="4.2" fill="#f4f8ff" />
          <circle cx="45" cy="32" r="4.2" fill="#f4f8ff" />
          <circle cx="28" cy="32" r="1.6" fill="#0b1f3a" />
          <circle cx="46" cy="32" r="1.6" fill="#0b1f3a" />
        </g>
      )}
      {celebrate ? (
        <path d="M24 46c4 6 20 6 24 0" fill="none" stroke="#f5b301" strokeWidth="2.4" strokeLinecap="round" />
      ) : (
        <path d="M28 46h16" stroke="#9ad7ff" strokeWidth="2" strokeLinecap="round" />
      )}
    </svg>
  );
}

/** Navy/gold traces. Each filled field lights the next segment. No animation loop. */
export function LitCircuits({ lit, total }: { lit: number; total: number }) {
  const count = Math.max(total, 1);
  const on = Math.max(0, Math.min(count, lit));
  return (
    <div className="mb-4 flex items-center justify-center gap-1.5" aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <span
          key={i}
          className="h-1.5 w-8 rounded-full transition-colors duration-200 motion-reduce:transition-none"
          style={{ background: i < on ? "#f5b301" : "rgba(255,255,255,0.22)" }}
        />
      ))}
    </div>
  );
}

export function passwordScore(password: string): number {
  if (!password) return 0;
  let score = 0;
  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1;
  if (/\d/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;
  return score;
}

const METER = [
  "",
  "Eish, that's a bit pap. A longer password travels further.",
  "Warming up. A number or a capital would help.",
  "Not bad — sharper than a Monday taxi queue.",
  "Lekker. That's a password with a backbone.",
  "Lekker. That's a password with a backbone.",
];

export function PasswordMeter({ password }: { password: string }) {
  const score = passwordScore(password);
  const label = score === 0 ? "Password strength" : score < 3 ? "Still light" : score < 4 ? "Solid" : "Strong";
  return (
    <div className="mt-2">
      <div className="flex gap-1" aria-hidden="true">
        {[1, 2, 3, 4, 5].map((n) => (
          <span
            key={n}
            className={`h-1.5 flex-1 rounded-full ${n <= score ? "" : "bg-ss-border"}`}
            style={n <= score ? { background: score >= 4 ? "#1a9e5f" : "#f5b301" } : undefined}
          />
        ))}
      </div>
      <p className="mt-1 text-xs text-ss-muted" role="status">
        {password ? `${label}. ${METER[score]}` : "At least 8 characters. A mix of letters and a number is kinder to future you."}
      </p>
    </div>
  );
}

/** Keep the server's meaning. Only soften the generic mismatch and a dead network. */
export function friendlyAuthError(message: string): string {
  const text = message.trim();
  if (/invalid (email|credentials)|incorrect password|wrong password/i.test(text)) {
    return "That email and password don't match. Have another look — the kettle's still on.";
  }
  if (/failed to fetch|network|load failed/i.test(text)) {
    return "We couldn't reach the server just then. It may be waking up. Try again in a moment.";
  }
  return text;
}

export function successPause(): Promise<void> {
  if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return Promise.resolve();
  }
  return new Promise((resolve) => window.setTimeout(resolve, 700));
}
