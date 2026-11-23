"use client";

import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { isValidEmail } from "@/lib/hustlePlay";

const SUCCESS = "You're on the list. We'll add you within about 24-48 hours, then open the download link again.";
const FIELD =
  "w-full rounded-xl border-2 border-[#C9CED6] bg-white px-4 py-3 text-base text-[#1F2328] placeholder:text-[#6B7079] focus:border-[#E2AE3C] focus:outline-none focus:ring-2 focus:ring-[#E2AE3C]/40";

/** "Request tester access" for the Gauteng Hustle Run closed test. Sends no email. */
export default function HustleTesterForm() {
  const { user } = useAuth();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [website, setWebsite] = useState(""); // honeypot, hidden from people
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const prefilled = useRef(false);

  useEffect(() => {
    if (user && !prefilled.current) {
      prefilled.current = true;
      setEmail((e) => e || user.email || "");
      setName((n) => n || [user.first_name, user.last_name].filter(Boolean).join(" "));
    }
  }, [user]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!isValidEmail(email)) {
      setError("Please enter a valid email address, for example yourname@gmail.com.");
      return;
    }
    setLoading(true);
    try {
      await api.post("/game/tester-requests", { email: email.trim(), name: name.trim() || undefined, website });
      setDone(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setError("Too many tries from this connection. Please wait a few minutes and try again.");
      } else if (err instanceof ApiError && err.status === 422) {
        setError("Please enter a valid email address, for example yourname@gmail.com.");
      } else {
        setError("We couldn't save your request just now. Our free server may be waking up, so please try again in a minute.");
      }
    } finally {
      setLoading(false);
    }
  }

  if (done) {
    return (
      <div role="status" className="rounded-2xl border-2 border-[#2E7D4F] bg-[#EEF8F1] p-5 text-[#1F2328]">
        <p className="text-lg font-extrabold">✅ {SUCCESS}</p>
        <p className="mt-2 text-sm text-[#3A3F47]">
          We added <strong>{email.trim().toLowerCase()}</strong>. When you&apos;re in, open the tester link first, then the
          download link above, on the phone signed in with this Google account.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} noValidate className="space-y-4">
      <div>
        <label htmlFor="hustle-email" className="mb-1.5 block text-base font-bold text-[#1F2328]">
          Google account email <span className="text-[#B8432A]">*</span>
        </label>
        <input
          id="hustle-email"
          type="email"
          inputMode="email"
          autoComplete="email"
          required
          maxLength={254}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="yourname@gmail.com"
          aria-describedby="hustle-email-help"
          aria-invalid={error ? true : undefined}
          className={FIELD}
        />
        <p id="hustle-email-help" className="mt-1.5 text-sm leading-relaxed text-[#3A3F47]">
          Use the Google account that is signed in to the Play Store on your Android phone. A Gmail address works best;
          other email addresses only work if they are already Google accounts.
        </p>
      </div>
      <div>
        <label htmlFor="hustle-name" className="mb-1.5 block text-base font-bold text-[#1F2328]">
          Name <span className="font-normal text-[#4A4F57]">(optional)</span>
        </label>
        <input
          id="hustle-name"
          type="text"
          autoComplete="name"
          maxLength={120}
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={FIELD}
        />
      </div>
      {/* Honeypot: hidden from people and screen readers; bots tend to fill it. */}
      <div aria-hidden="true" className="absolute -left-[9999px] h-px w-px overflow-hidden">
        <label htmlFor="hustle-website">Website</label>
        <input id="hustle-website" type="text" tabIndex={-1} autoComplete="off" value={website} onChange={(e) => setWebsite(e.target.value)} />
      </div>
      {error && (
        <p role="alert" className="rounded-xl border-2 border-[#B8432A] bg-[#FFF1EC] px-4 py-3 text-sm font-semibold text-[#8A2F17]">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={loading}
        className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-[#0B2447] px-6 py-3 text-base font-bold text-white shadow-md ring-2 ring-[#E2AE3C] transition hover:bg-[#13315E] disabled:cursor-not-allowed disabled:opacity-70 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0B6575] sm:w-auto"
      >
        {loading ? "Sending…" : "Request tester access"}
      </button>
      <p className="text-xs text-[#4A4F57]">
        We only use this email to add you to the game&apos;s tester list on Google Play. We don&apos;t send you emails.
      </p>
    </form>
  );
}
