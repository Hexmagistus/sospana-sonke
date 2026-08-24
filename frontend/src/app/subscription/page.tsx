"use client";

import Link from "next/link";
import Guard from "@/components/Guard";
import { Card, Button } from "@/components/ui";

// Subscriptions are temporarily removed — Sospana Sonke is free for now.
// This page is kept so old links/bookmarks land on a friendly notice instead
// of a checkout flow. Re-introduce billing here when the subscription returns.
function SubscriptionInner() {
  return (
    <div className="mx-auto max-w-xl space-y-4">
      <h1 className="text-2xl font-bold text-navy">Sospana Sonke is free 🎉</h1>
      <Card>
        <h2 className="mb-2 font-semibold">No subscription needed right now</h2>
        <p className="text-sm text-gray-600">
          While we grow across Southern Africa, every feature is free — browsing employers,
          tailoring your CV, cover letters, and application tracking are all included at no charge.
          There&apos;s nothing to pay and nothing to set up.
        </p>
        <div className="mt-4">
          <Link href="/companies">
            <Button>Browse companies →</Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}

export default function SubscriptionPage() {
  return (
    <Guard>
      <SubscriptionInner />
    </Guard>
  );
}
