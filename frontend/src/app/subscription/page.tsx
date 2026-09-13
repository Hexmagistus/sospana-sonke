"use client";

import Link from "next/link";
import Guard from "@/components/Guard";
import { Card, Button } from "@/components/ui";

// Subscriptions have been permanently removed — Sospana Sonke is free
// forever. This page is kept so old links/bookmarks land on a friendly
// notice instead of a checkout flow.
function SubscriptionInner() {
  return (
    <div className="mx-auto max-w-xl space-y-4">
      <h1 className="text-2xl font-bold text-navy">Sospana Sonke is free forever 🎉</h1>
      <Card>
        <h2 className="mb-2 font-semibold">No subscription — not now, not ever</h2>
        <p className="text-sm text-gray-600">
          Every feature is free, for good — browsing employers, direct careers links, CV
          tailoring, and application tracking are all included at no charge.
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
