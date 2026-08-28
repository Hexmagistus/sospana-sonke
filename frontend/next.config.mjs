/** @type {import('next').NextConfig} */

// NOTE: no Content-Security-Policy here. A CSP has to name every host the app
// talks to (backend API, Google sign-in, logo providers) exactly right, and
// getting it wrong fails silently in the browser — requests just get dropped,
// which is what broke login. Ship the headers below (safe, can't break a
// working feature) and add a CSP back later with it tested end-to-end first.
const securityHeaders = [
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
