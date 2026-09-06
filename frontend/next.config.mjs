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
  "connect-src 'self' https://sospana-sonke-api.onrender.com https://accounts.google.com https://apis.google.com",
  "frame-src https://accounts.google.com",
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
  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders,
      },
    ];
  },
};

export default nextConfig;
