import type { Metadata } from "next";
import { Fraunces, Outfit } from "next/font/google";
import { I18nProvider } from "@/components/i18n-provider";
import { siteUrl } from "@/lib/utils";
import "./globals.css";

const display = Fraunces({ subsets: ["latin"], variable: "--font-display", display: "swap" });
const sans = Outfit({ subsets: ["latin"], variable: "--font-sans", display: "swap" });

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl()),
  title: { default: "SOSPANA CINEMA", template: "%s · SOSPANA CINEMA" },
  description: "Free Entertainment. Everywhere. A free, no-login catalogue of public-domain, openly licensed and rights-holder-embedded films and series.",
  applicationName: "SOSPANA CINEMA",
  openGraph: {
    siteName: "SOSPANA CINEMA",
    title: "SOSPANA CINEMA",
    description: "Free Entertainment. Everywhere.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable}`}>
      <body className="font-sans antialiased">
        <a href="#content" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-amber focus:px-3 focus:py-2 focus:text-stone-950">
          Skip to content
        </a>
        <I18nProvider>{children}</I18nProvider>
      </body>
    </html>
  );
}
