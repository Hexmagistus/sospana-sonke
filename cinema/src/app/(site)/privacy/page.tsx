import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy",
  description: "What Sospana Cinema stores, and what it does not.",
  alternates: { canonical: "/privacy" },
};

export default function PrivacyPage() {
  return (
    <main className="max-w-2xl space-y-4 text-sm leading-6 text-ink/80">
      <h1 className="font-display text-4xl text-ink">Privacy</h1>
      <p>Sospana Cinema is free to watch. Viewers are not asked to register, sign in, or pay. Favourites, continue watching, search history and the country you pick are stored in this browser. The Clear local data button deletes them.</p>
      <p>A copyright complaint stores the name, email, title and reason you send, so the complaint can be answered. That is the only personal information the public site asks for, and only if you choose to write in.</p>
      <p>The admin sign-in is separate. It is not a viewer account. Admin sessions use an httpOnly cookie.</p>
      <p>The demonstration catalogue does not run behavioural advertising, and Kids Cinema does not build a profile of a child.</p>
      <p>If Supabase is configured, published catalogue rows are read from that database. Complaint rows are not readable by the public key.</p>
    </main>
  );
}
