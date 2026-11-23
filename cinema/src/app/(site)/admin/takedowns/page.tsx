import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { currentAdmin } from "@/lib/session";
import { adminTakedowns } from "@/lib/admin-takedowns";

export const metadata: Metadata = { title: "Complaints", robots: { index: false } };

export default async function TakedownsPage() {
  const admin = await currentAdmin();
  if (!admin) redirect("/admin/login");
  const { items, origin, warning } = await adminTakedowns();
  return (
    <main>
      <h1 className="font-display text-4xl">Copyright complaints</h1>
      <p className="mt-2 text-sm text-ink/60">Source: {origin}.</p>
      {warning ? <p className="mt-2 text-sm text-coral">{warning}</p> : null}
      {items.length === 0 && !warning ? <p className="mt-4 text-sm text-ink/70">No complaints have been stored yet.</p> : null}
      <ul className="mt-6 space-y-3">
        {items.map((item) => (
          <li key={item.id} className="rounded-2xl border border-white/10 p-4 text-sm">
            <p className="font-semibold">{item.contentId} · {item.status} · {item.createdAt.slice(0, 10)}</p>
            <p className="text-ink/60">{item.claimantName} · {item.contactEmail}</p>
            <p className="mt-2">{item.reason}</p>
          </li>
        ))}
      </ul>
    </main>
  );
}
