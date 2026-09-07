"use client";

import Link from "next/link";
import { Card, Button } from "@/components/ui";

export default function DonateThanksPage() {
  return (
    <div className="mx-auto max-w-xl space-y-4">
      <Card>
        <h1 className="text-2xl font-bold text-navy">Thank you 🙏</h1>
        <p className="mt-2 text-sm text-gray-600">
          Your support helps keep Sospana Sonke free for jobseekers across Southern Africa. A
          receipt has been sent to the email address you provided.
        </p>
        <div className="mt-4">
          <Link href="/companies">
            <Button>Back to Sospana Sonke →</Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}
