// Central SEO / site constants. Keep the URL in sync with the production domain.
export const SITE_URL = "https://sospana-sonke.vercel.app";
export const SITE_NAME = "Sospana Sonke";
export const SITE_TAGLINE = "Born in SADC, built for the world";
export const SITE_DESCRIPTION =
  "Sospana Sonke started in the SADC region. It stores jobs, internships, learnerships, bursaries and graduate programmes from official pages, lists employers with a direct careers link, and shows the Statistics South Africa labour table. A search answer uses only what is stored. You apply on the source page. The tools are free. We do not promise a place.";
export const SITE_KEYWORDS = [
  "jobs in South Africa",
  "learnerships",
  "bursaries",
  "graduate programmes",
  "internships",
  "government jobs",
  "careers pages",
  "Stats SA unemployment",
  "apply directly",
  "SADC jobs",
  "verified employers",
  "Sospana Sonke",
];
// Public, indexable routes. Must NOT include anything wrapped in <Guard> --
// see the disallow list in robots.ts, which this should stay consistent with.
export const PUBLIC_ROUTES = [
  "/",
  "/jobs",
  "/opportunities",
  "/countries",
  "/employers",
  "/donate",
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/privacy",
  "/terms",
];
