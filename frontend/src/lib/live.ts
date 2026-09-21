import type { Company } from "@/lib/types";

// A "live" link is one the URL tester (or a researcher's confirmation at import time) has
// verified lands on the employer's own careers page. Only these are linked and shown up top.
export const isLive = (c: Company) => !!c.careers_url && c.scraping_status === "ok";
