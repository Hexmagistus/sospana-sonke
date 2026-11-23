import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { currentAdmin } from "@/lib/session";
import { listTakedowns } from "@/lib/store";

export const metadata: Metadata = { title: "Complaints", robots: { index: false } };

export default async function TakedownsPage() {
  const admin = await currentAdmin();
  if (!admin) redirect("/admin/login");
  const items = listTakedowns();
  return (
    <main>
      <h1 className="font-display text-4xl">Copyright complaints</h1>
      {items.length === 0 ? <p className="mt-4 text-sm text-ink/70">No complaints have been stored on this server.</p> : null}
      <ul className="mt-6 space-y-3">
        {items.map((item) => (
          <li key={item.id} className="rounded-2xl border border-white/10 p-4 text-sm">
            <p className="font-semibold">{item.contentId} · {item.status}</p>
            <p className="text-ink/60">{item.claimantName} · {item.contactEmail}</p>
            <p className="mt-2">{item.reason}</p>
          </li>
        ))}
      </ul>
    </main>
  );
}
