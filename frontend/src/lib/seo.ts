// Central SEO / site constants. Keep the URL in sync with the production domain.
export const SITE_URL = "https://sospana-sonke.vercel.app";
export const SITE_NAME = "Sospana Sonke";
export const SITE_TAGLINE = "Born in SADC, built for the world";
export const SITE_DESCRIPTION =
  "Sospana Sonke started in the SADC region. It lists employers with a direct link to their own careers page across Africa, Oceania, Europe, South America, North America and Asia. You apply on the employer's site. The tools are free. We do not promise a job.";
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
  "/forgot-password",
  "/reset-password",
  "/privacy",
  "/terms",
];
