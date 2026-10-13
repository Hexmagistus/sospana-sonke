import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "For organisations",
  description:
    "Claim your employer page with an email on your own domain, or ask an administrator to check the claim. Job seekers are not charged.",
  alternates: { canonical: "/for-organisations" },
};

export default function ForOrganisationsPage() {
  return (
    <article className="mx-auto max-w-3xl space-y-4">
      <header className="space-y-2">
        <p className="text-sm font-semibold text-ss-primary">Organisations</p>
        <h1 className="font-display text-3xl font-bold text-ss-text">Claim your employer page</h1>
      </header>
      <div className="ss-card space-y-3 text-sm leading-relaxed text-ss-text">
        <p>
          An organisation account is separate from a job-seeker account. Search, alerts, and CV tools stay free
          for people looking for work.
        </p>
        <p>
          To claim a page, create an organisation account and send an email address on the same domain as the
          careers link or the official website in the directory. We mail that address a confirmation link. A free
          inbox such as Gmail does not confirm the domain. If you cannot use a domain address, ask an administrator
          to check the claim.
        </p>
        <p>
          The free plan lets a verified organisation submit corrections and a small number of opportunities. Every
          opportunity is checked before it is listed, and it is labelled employer-submitted. Employer Pro and a
          featured listing have prices in rand. Those prices stay unpublished until the owner sets them.
        </p>
        <p>
          Card numbers are entered on Paystack, in test mode until the owner turns on a live account. This server
          does not store the card.
        </p>
      </div>
      <p className="flex flex-wrap gap-3 text-sm">
        <Link href="/organisation/register" className="inline-flex min-h-11 items-center rounded-xl bg-gold px-4 py-2 font-semibold text-navy">
          Create an organisation account
        </Link>
        <Link href="/organisation" className="inline-flex min-h-11 items-center rounded-xl bg-navy px-4 py-2 font-semibold text-white">
          Organisation home
        </Link>
        <Link href="/pricing" className="inline-flex min-h-11 items-center font-semibold text-navy underline">
          Pricing
        </Link>
      </p>
    </article>
  );
}
