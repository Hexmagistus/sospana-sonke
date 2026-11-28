/** @type {import('next').NextConfig} */

// Content-Security-Policy is shipped in REPORT-ONLY mode below: an enforced CSP
// has to name every host the app talks to (backend API, Google sign-in, logo
// providers) exactly right, and a wrong directive fails silently — requests get
// dropped, which is what broke login before. Report-Only lets the browser report
// violations without blocking anything, so it is safe to ship. Review reports in
// production, then rename the header to "Content-Security-Policy" to enforce.
const contentSecurityPolicy = [
  "default-src 'self'",
  "base-uri 'self'",
  "object-src 'none'",
  "frame-ancestors 'none'",
  "form-action 'self'",
  // Next.js injects inline bootstrap scripts (no nonce configured), and Google
  // Identity Services loads from accounts.google.com.
  "script-src 'self' 'unsafe-inline' https://accounts.google.com https://apis.google.com",
  "style-src 'self' 'unsafe-inline'",
  // Company logos come from Clearbit / Google favicons / arbitrary official sites.
  "img-src 'self' data: https:",
  "font-src 'self' data:",
  // Backend API (Render) + Google sign-in token endpoints.
  "connect-src 'self' https://sospana-sonke-api-fra.onrender.com https://accounts.google.com https://apis.google.com",
  // Google sign-in, plus Bandcamp's official embedded player (bandcamp.com and artist subdomains).
  "frame-src https://accounts.google.com https://bandcamp.com https://*.bandcamp.com",
].join("; ");
const securityHeaders = [
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()" },
  { key: "X-XSS-Protection", value: "0" },
  // Report-Only so a mis-scoped directive can't silently break login/API calls.
  { key: "Content-Security-Policy-Report-Only", value: contentSecurityPolicy },
];

const nextConfig = {
  reactStrictMode: true,
  // Lint is run separately; don't fail production builds on lint.
  eslint: { ignoreDuringBuilds: true },
  // Sign-in is switched off: every page is public, so the account pages send people home.
  async redirects() {
    return [
      // The /jobs listing and job detail pages were removed (Nov 2026).
      { source: "/jobs", destination: "/opportunities-today", permanent: true },
      { source: "/jobs/:path*", destination: "/opportunities-today", permanent: true },
      // Account and admin pages were removed (Nov 2026); old links go home.
      { source: "/login", destination: "/", permanent: true },
      { source: "/login/:path*", destination: "/", permanent: true },
      { source: "/register", destination: "/", permanent: true },
      { source: "/register/:path*", destination: "/", permanent: true },
      { source: "/forgot-password", destination: "/", permanent: true },
      { source: "/forgot-password/:path*", destination: "/", permanent: true },
      { source: "/reset-password", destination: "/", permanent: true },
      { source: "/reset-password/:path*", destination: "/", permanent: true },
      { source: "/dashboard", destination: "/", permanent: true },
      { source: "/dashboard/:path*", destination: "/", permanent: true },
      { source: "/applications", destination: "/", permanent: true },
      { source: "/applications/:path*", destination: "/", permanent: true },
      { source: "/profile", destination: "/", permanent: true },
      { source: "/profile/:path*", destination: "/", permanent: true },
      { source: "/messages", destination: "/", permanent: true },
      { source: "/messages/:path*", destination: "/", permanent: true },
      { source: "/notifications", destination: "/", permanent: true },
      { source: "/notifications/:path*", destination: "/", permanent: true },
      { source: "/preferences", destination: "/", permanent: true },
      { source: "/preferences/:path*", destination: "/", permanent: true },
      { source: "/master-cv", destination: "/", permanent: true },
      { source: "/master-cv/:path*", destination: "/", permanent: true },
      { source: "/tailor", destination: "/", permanent: true },
      { source: "/tailor/:path*", destination: "/", permanent: true },
      { source: "/subscription", destination: "/", permanent: true },
      { source: "/subscription/:path*", destination: "/", permanent: true },
      { source: "/cv-audit", destination: "/", permanent: true },
      { source: "/cv-audit/:path*", destination: "/", permanent: true },
      { source: "/agent", destination: "/", permanent: true },
      { source: "/agent/:path*", destination: "/", permanent: true },
      { source: "/organisation", destination: "/", permanent: true },
      { source: "/organisation/:path*", destination: "/", permanent: true },
      { source: "/admin", destination: "/", permanent: true },
      { source: "/admin/:path*", destination: "/", permanent: true },
      { source: "/pricing", destination: "/", permanent: true },
      { source: "/pricing/:path*", destination: "/", permanent: true },
      // The programmes page was retired (Nov 2026); old links land on today's checked posts.
      { source: "/opportunities", destination: "/opportunities-today", permanent: true },
      { source: "/opportunities/:path*", destination: "/opportunities-today", permanent: true },
    ];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders,
      },
      {
        // AI-training opt-out on the careers directory. Not noindex: Google keeps indexing.
        source: "/countries/:path*",
        headers: [{ key: "X-Robots-Tag", value: "noai, noimageai" }],
      },
      {
        // Game service worker + precache list must update quickly.
        source: "/game/sw.js",
        headers: [
          { key: "Cache-Control", value: "no-cache, max-age=0, must-revalidate" },
          { key: "Service-Worker-Allowed", value: "/game/" },
        ],
      },
      {
        source: "/game/precache.json",
        headers: [{ key: "Cache-Control", value: "no-cache, max-age=0, must-revalidate" }],
      },
      {
        source: "/sa-careers",
        headers: [{ key: "X-Robots-Tag", value: "noai, noimageai" }],
      },
      {
        source: "/",
        headers: [{ key: "Cache-Control", value: "public, s-maxage=300, stale-while-revalidate=600" }],
      },
      {
        source: "/opportunities",
        headers: [{ key: "Cache-Control", value: "public, s-maxage=60, stale-while-revalidate=120" }],
      },
      {
        source: "/opportunities/:path*",
        headers: [{ key: "Cache-Control", value: "public, s-maxage=60, stale-while-revalidate=120" }],
      },
      {
        source: "/feed.xml",
        headers: [{ key: "Cache-Control", value: "public, s-maxage=60, stale-while-revalidate=120" }],
      },
      {
        source: "/feed.json",
        headers: [{ key: "Cache-Control", value: "public, s-maxage=60, stale-while-revalidate=120" }],
      },
      {
        source: "/data",
        headers: [{ key: "Cache-Control", value: "public, s-maxage=300, stale-while-revalidate=600" }],
      },
      {
        source: "/pricing",
        headers: [{ key: "Cache-Control", value: "public, s-maxage=300, stale-while-revalidate=600" }],
      },
      {
        source: "/employers",
        headers: [{ key: "Cache-Control", value: "public, s-maxage=300, stale-while-revalidate=600" }],
      },
      {
        source: "/employers/:path*",
        headers: [{ key: "Cache-Control", value: "public, s-maxage=300, stale-while-revalidate=600" }],
      },
      {
        // Landmark photos are replaced rarely and are the heaviest bytes on
        // the landing page. A week of shared caching avoids re-downloading
        // them on every visit without pinning a swapped file for a year.
        source: "/photos/:path*",
        headers: [{ key: "Cache-Control", value: "public, max-age=604800, stale-while-revalidate=86400" }],
      },
    ];
  },
};

export default nextConfig;
