import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import Nav from "@/components/Nav";
import PwaRegister from "@/components/PwaRegister";

export const metadata: Metadata = {
  title: "Sospana Sonke",
  description: "AI-powered job discovery, CV tailoring and applications for South Africa.",
  manifest: "/manifest.webmanifest",
  applicationName: "Sospana Sonke",
  icons: {
    icon: "/icons/icon-192.png",
    apple: "/icons/apple-touch-icon.png",
  },
  appleWebApp: {
    capable: true,
    title: "Sospana Sonke",
    statusBarStyle: "default",
  },
};

export const viewport: Viewport = {
  themeColor: "#0f766e",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <PwaRegister />
        <AuthProvider>
          <Nav />
          <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
