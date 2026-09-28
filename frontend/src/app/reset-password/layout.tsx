import type { Metadata } from "next";
import { Suspense } from "react";

export const metadata: Metadata = {
  title: "Choose a new password",
  description: "Set a new Sospana Sonke password with the token from your email.",
  alternates: { canonical: "/reset-password" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={null}>{children}</Suspense>;
}
