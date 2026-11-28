import type { Metadata } from "next";
import HustleTesterForm from "@/components/HustleTesterForm";
import { HUSTLE_PLAY_NAME, HUSTLE_PLAY_URL, HUSTLE_TESTING_URL } from "@/lib/hustlePlay";

export const metadata: Metadata = {
  title: "Download Gauteng Hustle Run for Android | Sospana Sonke",
  description:
    "Get Gauteng Hustle Run (listed on Google Play as Bond Village Hustle) on your Android phone. The game is in testing: join the tester list, then download it from Google Play.",
};

const CARD = "rounded-3xl border-2 border-[#E2AE3C]/60 bg-white p-5 shadow-[0_22px_44px_-26px_rgba(11,36,71,0.35)] sm:p-7";
const FOCUS = "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0B6575]";

export default function HustleRunPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6 text-[#1F2328]">
      <section id="download" className={CARD} aria-labelledby="hustle-download-title">
        <p className="text-sm font-bold uppercase tracking-[0.12em] text-[#7A5200]">🎮 Android game · in testing</p>
        <h1 id="hustle-download-title" className="mt-2 text-3xl font-extrabold leading-tight sm:text-4xl">
          Download Gauteng Hustle Run
        </h1>
        <p className="mt-2 text-base font-semibold text-[#0B2447]">
          Listed on Google Play as <span className="whitespace-nowrap">&ldquo;{HUSTLE_PLAY_NAME}&rdquo;</span>.
        </p>
        <p className="mt-4 text-lg leading-relaxed text-[#3A3F47]">
          Gauteng Hustle Run is in testing on Google Play, so for now only people on our tester list can install it.
          Testers: open the tester link once, tap <strong>Become a tester</strong>, then download the game.
        </p>
        <ol className="mt-5 space-y-3">
          <li className="flex gap-3">
            <span aria-hidden="true" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#0B2447] font-bold text-white">1</span>
            <div className="min-w-0">
              <a href={HUSTLE_TESTING_URL} target="_blank" rel="noopener noreferrer" className={`inline-flex items-center gap-2 rounded-full border-2 border-[#0B2447] bg-white px-5 py-2.5 text-base font-bold text-[#0B2447] hover:bg-[#F3F6FB] ${FOCUS}`}>
                Join the test (opt in) →
              </a>
              <p className="mt-1 text-sm text-[#4A4F57]">Do this once, signed in with the Google account on your phone.</p>
            </div>
          </li>
          <li className="flex gap-3">
            <span aria-hidden="true" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#0B2447] font-bold text-white">2</span>
            <div className="min-w-0">
              <a href={HUSTLE_PLAY_URL} target="_blank" rel="noopener noreferrer" className={`inline-flex items-center gap-2 rounded-full bg-[#B8432A] px-5 py-2.5 text-base font-bold text-white shadow-md ring-2 ring-[#E2AE3C]/70 hover:bg-[#9A3722] ${FOCUS}`}>
                ▶ Get it on Google Play
              </a>
              <p className="mt-1 text-sm text-[#4A4F57]">Opens the game on the Play Store so you can install it.</p>
            </div>
          </li>
        </ol>
        <p className="mt-5 rounded-2xl bg-[#FFF8EC] px-4 py-3 text-base leading-relaxed text-[#3A3F47]">
          <strong>Does Google Play say the app &ldquo;isn&apos;t available&rdquo; to you?</strong> Your Google account
          isn&apos;t on the tester list yet. Request access below and we&apos;ll add you.
        </p>
        <p className="mt-3 text-sm text-[#4A4F57]">
          No Android phone? <a href="/game/play.html" className="font-semibold text-[#0B6575] underline">Play the free web version</a> in your browser.
        </p>
      </section>

      <section id="request-access" className={CARD} aria-labelledby="hustle-request-title">
        <h2 id="hustle-request-title" className="text-2xl font-extrabold">Request tester access</h2>
        <p className="mt-2 mb-5 text-base leading-relaxed text-[#3A3F47]">
          Leave your Google account email and we&apos;ll add it to the Gauteng Hustle Run tester list on Google Play.
        </p>
        <HustleTesterForm />
      </section>
    </div>
  );
}
