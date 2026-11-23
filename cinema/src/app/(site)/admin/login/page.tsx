import type { Metadata } from "next";
import { LoginForm } from "@/components/admin-client";

export const metadata: Metadata = { title: "Admin sign-in", robots: { index: false, follow: false } };

export default function AdminLoginPage() {
  return (
    <main>
      <h1 className="font-display text-4xl">Admin</h1>
      <p className="mt-3 max-w-xl text-sm text-ink/70">
        This sign-in is only for the people who look after the catalogue. Viewers never need it. The password is read from the server environment, not from the page.
      </p>
      <div className="mt-6">
        <LoginForm />
      </div>
    </main>
  );
}
