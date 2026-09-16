import type { Metadata, Viewport } from "next";
import { Space_Grotesk } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import Nav from "@/components/Nav";
import MobileBottomNav from "@/components/MobileBottomNav";
import PwaRegister from "@/components/PwaRegister";
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
        <AuthProvider>
          <Nav />
          <main id="main-content" className="mx-auto max-w-6xl px-4 py-6 pb-24 md:pb-6">
            {children}
          </main>
          <MobileBottomNav />
        </AuthProvider>
      </body>
    </html>
  );
}
