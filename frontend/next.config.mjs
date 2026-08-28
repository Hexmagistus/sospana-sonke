/** @type {import('next').NextConfig} */

// Content-Security-Policy: only the origins this app actually talks to.
// - logo.clearbit.com / www.google.com (s2/favicons): real employer logos in CompanyLogo.tsx
// - accounts.google.com: "Sign in with Google" (script + auth iframe)
// - *.onrender.com: the FastAPI backend (Render); *.vercel.app: this app's own preview/prod domains
// Fonts are self-hosted at build time via next/font, so no fonts.googleapis.com/gstatic.com call is needed.
const csp = [
  "default-src 'self'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "object-src 'none'",
  "script-src 'self' https://accounts.google.com",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https://logo.clearbit.com https://www.google.com https://*.googleusercontent.com",
  "font-src 'self' data:",
  "connect-src 'self' https://accounts.google.com https://*.onrender.com https://*.vercel.app",
  "frame-src https://accounts.google.com",
  "upgrade-insecure-requests",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()" },
  { key: "X-XSS-Protection", value: "0" },
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
