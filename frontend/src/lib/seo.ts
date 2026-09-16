// Central SEO / site constants. Keep the URL in sync with the production domain.
export const SITE_URL = "https://sospana-sonke.vercel.app";
export const SITE_NAME = "Sospana Sonke";
export const SITE_TAGLINE = "Find verified employers across Africa";
export const SITE_DESCRIPTION =
  "Discover verified employers across Africa — private companies, state-owned enterprises, government departments and municipalities — and apply directly on their official careers pages. No middleman job boards.";
export const SITE_KEYWORDS = [
  "jobs in Africa",
  "African job vacancies",
  "government jobs",
  "municipality vacancies",
  "state-owned enterprise jobs",
  "careers pages",
  "apply directly",
  "South Africa jobs",
  "SADC jobs",
  "verified employers",
  "Sospana Sonke",
];
// Public, indexable routes. Must NOT include anything wrapped in <Guard> --
// see the disallow list in robots.ts, which this should stay consistent with.
export const PUBLIC_ROUTES = [
  "/",
  "/donate",
  "/login",
  "/register",
  "/privacy",
  "/terms",
];
