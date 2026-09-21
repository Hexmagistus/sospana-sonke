import type { Metadata, Viewport } from "next";
import { Space_Grotesk } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { ThemeProvider, THEME_BOOTSTRAP_SCRIPT } from "@/lib/theme";
import Nav from "@/components/Nav";
import MobileBottomNav from "@/components/MobileBottomNav";
import CommandPalette from "@/components/CommandPalette";
import PwaRegister from "@/components/PwaRegister";
import PolicyConsent from "@/components/PolicyConsent";
import MentionPopup from "@/components/MentionPopup";
import PwaExtras from "@/components/PwaExtras";
import CopyGuard from "@/components/CopyGuard";
import { SITE_URL, SITE_NAME, SITE_TAGLINE, SITE_DESCRIPTION, SITE_KEYWORDS } from "@/lib/seo";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: `${SITE_NAME} — ${SITE_TAGLINE}`,
    template: `%s · ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  keywords: SITE_KEYWORDS,
  applicationName: SITE_NAME,
  manifest: "/manifest.webmanifest",
  alternates: { canonical: "/" },
  category: "employment",
  icons: {
    icon: "/icons/icon-192.png",
    apple: "/icons/apple-touch-icon.png",
  },
  appleWebApp: {
    capable: true,
    title: SITE_NAME,
    statusBarStyle: "default",
  },
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: SITE_NAME,
    title: `${SITE_NAME} — ${SITE_TAGLINE}`,
    description: SITE_DESCRIPTION,
    locale: "en_ZA",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Sospana Sonke — find verified employers across Africa",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: `${SITE_NAME} — ${SITE_TAGLINE}`,
    description: SITE_DESCRIPTION,
    images: ["/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
};

export const viewport: Viewport = {
  themeColor: "#0f766e",
  width: "device-width",
  initialScale: 1,
};

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": `${SITE_URL}/#organization`,
      name: SITE_NAME,
      url: SITE_URL,
      logo: `${SITE_URL}/logo-full.png`,
      description: SITE_DESCRIPTION,
      areaServed: "Africa",
    },
    {
      // No SearchAction here: the one place a keyword search actually lives
      // (`/companies`) requires login, and schema.org's own guidance is that a
      // SearchAction target must be usable without authentication -- pointing
      // it at a gated page would just send crawlers into a login redirect.
      "@type": "WebSite",
      "@id": `${SITE_URL}/#website`,
      name: SITE_NAME,
      url: SITE_URL,
      description: SITE_DESCRIPTION,
      publisher: { "@id": `${SITE_URL}/#organization` },
      inLanguage: "en",
    },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={spaceGrotesk.variable}>
      <head>
        <Script id="ss-theme-bootstrap" strategy="beforeInteractive">
          {THEME_BOOTSTRAP_SCRIPT}
        </Script>
      </head>
      <body>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        <PwaRegister />
        <CopyGuard />
        <a
          href="#main-content"
          className="sr-only focus-visible:not-sr-only focus-visible:fixed focus-visible:left-4 focus-visible:top-4 focus-visible:z-50 focus-visible:rounded-md focus-visible:bg-navy focus-visible:px-4 focus-visible:py-2 focus-visible:text-white"
        >
          Skip to main content
        </a>
        <ThemeProvider>
          <AuthProvider>
            <Nav />
            <main id="main-content" className="mx-auto max-w-6xl px-4 py-6 pb-24 md:pb-6">
              {children}
            </main>
            <footer className="mx-auto max-w-6xl px-4 pb-28 pt-8 md:pb-12">
              <div
                className="mx-auto max-w-2xl rounded-2xl border border-ss-tech/30 bg-ss-surface/60 px-5 py-4 text-center backdrop-blur-sm"
                style={{ boxShadow: "0 0 34px var(--ss-tech-glow)" }}
              >
                <p className="text-sm font-semibold leading-relaxed sm:text-base">
                  <span className="text-xl align-middle">🐢💨</span>{" "}
                  <span className="animate-gradient-text bg-gradient-to-r from-[#22d3ee] via-[#f5b301] to-[#a78bfa] bg-clip-text font-extrabold text-transparent">
                    Our server rides the free tier
                  </span>{" "}
                  — so it can be a little slow to wake up, and we&apos;re actively speeding it up. We keep Sospana Sonke{" "}
                  <span className="font-extrabold text-ss-primary" style={{ textShadow: "0 0 18px var(--ss-primary-glow)" }}>free for everyone</span>, always. 💛
                </p>
              </div>
              <p className="mx-auto mt-4 max-w-2xl text-center text-xs leading-relaxed text-ss-muted">
                Organisation names and logos belong to their owners; listing them does not imply
                partnership or endorsement.{" "}
                <a href="/privacy" className="underline hover:text-ss-text">Privacy</a>
                {" · "}
                <a href="/terms" className="underline hover:text-ss-text">Terms</a>
              </p>
            </footer>
            <PwaExtras />
            <MobileBottomNav />
            <PolicyConsent />
            <MentionPopup />
            <CommandPalette />
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
