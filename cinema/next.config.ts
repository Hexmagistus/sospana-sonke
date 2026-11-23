import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  images: {
    unoptimized: true,
    remotePatterns: [
      { protocol: "https", hostname: "archive.org" },
      { protocol: "https", hostname: "**.archive.org" },
      { protocol: "https", hostname: "i.ytimg.com" },
    ],
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
  async redirects() {
    const pairs: Array<[string, string]> = [
      ["/international", "/categories/international-movies"],
      ["/african-cinema", "/categories/african-cinema"],
      ["/south-african-movies", "/categories/south-african-movies"],
      ["/animation", "/categories/animated-movies"],
      ["/cartoons", "/categories/cartoons"],
      ["/documentaries", "/categories/documentaries"],
      ["/classic", "/categories/classic-cinema"],
      ["/family", "/categories/family-entertainment"],
      ["/educational", "/categories/educational-movies"],
    ];
    return pairs.map(([source, destination]) => ({ source, destination, permanent: false }));
  },
};

export default nextConfig;
