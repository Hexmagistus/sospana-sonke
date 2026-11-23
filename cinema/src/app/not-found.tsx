import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto max-w-xl px-4 py-20">
      <h1 className="font-display text-4xl">That page is not in the catalogue</h1>
      <p className="mt-3 text-sm text-ink/70">The address does not match a published title or section.</p>
      <Link href="/" className="mt-6 inline-block text-amber">
        Back to Sospana Cinema
      </Link>
    </main>
  );
}
