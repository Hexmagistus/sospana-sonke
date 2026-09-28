import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Reset password",
  description: "Request a password reset token for your Sospana Sonke account.",
  alternates: { canonical: "/forgot-password" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
