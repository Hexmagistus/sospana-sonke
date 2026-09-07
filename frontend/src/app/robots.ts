import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // Keep private / authenticated / user-specific areas out of the index.
        disallow: [
          "/admin",
          "/dashboard",
          "/profile",
          "/matches",
          "/notifications",
          "/subscription",
          "/tailor",
          "/security",
          "/api/",
        ],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
