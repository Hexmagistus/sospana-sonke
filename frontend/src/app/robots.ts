import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      // AI-training and bulk scraper crawlers (list from PR #161). robots.txt is honoured only by
      // polite bots; the Vercel Firewall rule enforces the block for the same user agents.
      {
        userAgent: [
          "GPTBot", "ChatGPT-User", "OAI-SearchBot", "CCBot", "ClaudeBot", "Claude-Web", "anthropic-ai",
          "Google-Extended", "Applebot-Extended", "PerplexityBot", "Bytespider", "Amazonbot", "meta-externalagent",
          "FacebookBot", "cohere-ai", "Diffbot", "ImagesiftBot", "Omgilibot", "Timpibot", "YouBot",
          "AhrefsBot", "SemrushBot", "MJ12bot", "DotBot", "DataForSeoBot", "PetalBot", "BLEXBot", "Scrapy",
        ],
        disallow: "/",
      },
      {
        userAgent: "*",
        allow: "/",
        // Keep private / authenticated / user-specific areas out of the index.
        // This list should mirror every page.tsx that wraps itself in <Guard> --
        // a page that requires login has nothing indexable behind it (a crawler
        // just gets a login redirect), so leaving it crawlable wastes crawl
        // budget and risks a bot indexing an empty/misleading shell page.
        // /jobs, /countries, /countries/<slug> and /employers stay allowed: they are public.
        // /companies stays disallowed because it requires sign-in.
        disallow: [
          "/admin",
          "/organisation",
          "/dashboard",
          "/profile",
          "/matches",
          "/notifications",
          "/subscription",
          "/tailor",
          "/cv-audit",
          "/security",
          "/companies",
          "/coverage",
          "/agent",
          "/master-cv",
          "/universities",
          "/colleges",
          "/hospitals",
          "/ngos",
          "/government",
          "/applications",
          "/api/",
        ],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
