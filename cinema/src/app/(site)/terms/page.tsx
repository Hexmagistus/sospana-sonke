import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Terms",
  description: "How Sospana Cinema lists and plays films.",
  alternates: { canonical: "/terms" },
};

export default function TermsPage() {
  return (
    <main className="max-w-2xl space-y-4 text-sm leading-6 text-ink/80">
      <h1 className="font-display text-4xl text-ink">Terms</h1>
      <p>Sospana Cinema lists films only when a source record carries a public-domain mark, CC0, or a Creative Commons licence that allows reuse (CC BY or CC BY-SA), or when the rights holder itself publishes the full title for embedding on its own official channel. Non-commercial and no-derivatives licences are refused for hosted files. Some titles are instead played through the official YouTube embed published by the rights holder on its own channel; Sospana Cinema does not copy or host those files, and the channel is recorded as the evidence. A title without that evidence is not given a Watch now button.</p>
      <p>Playback uses the provider&apos;s own player or a file on the same public item. Sospana Cinema does not rehost those files and does not offer a download button.</p>
      <p>Public-domain status can differ by country. A worldwide mark on a source record is not a promise that every territory treats the work the same way. This site does not claim zero legal risk.</p>
      <p>
        If a listing is wrong, use the <Link href="/takedown" className="text-amber">copyright complaint form</Link>.
      </p>
    </main>
  );
}
