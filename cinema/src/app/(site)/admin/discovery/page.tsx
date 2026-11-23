import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { archiveCandidate } from "@/lib/licence";
import { currentAdmin } from "@/lib/session";

export const metadata: Metadata = { title: "Discovery", robots: { index: false } };

const sample = [
  { identifier: "night-of-the-living-dead_1968", title: "Night of the Living Dead", licenseurl: "https://creativecommons.org/publicdomain/mark/1.0/" },
  { identifier: "BigBuckBunny", title: "Big Buck Bunny", licenseurl: "https://creativecommons.org/licenses/by/3.0/" },
  { identifier: "rejected-sample", title: "A non-commercial upload", licenseurl: "https://creativecommons.org/licenses/by-nc-sa/4.0/" },
  { identifier: "no-licence", title: "Untitled upload", licenseurl: "" },
];

export default async function DiscoveryPage() {
  const admin = await currentAdmin();
  if (!admin) redirect("/admin/login");
  const discoveryUrl = process.env.DISCOVERY_URL;
  let health = "DISCOVERY_URL is not set, so this page cannot reach the Python discovery service.";
  if (discoveryUrl) {
    try {
      const response = await fetch(`${discoveryUrl.replace(/\/$/, "")}/health`, { cache: "no-store" });
      const text = await response.text();
      health = response.ok ? `Discovery service answered: ${text.slice(0, 300)}` : `Discovery service returned HTTP ${response.status}: ${text.slice(0, 300)}`;
    } catch (error) {
      health = `The discovery service could not be reached: ${error instanceof Error ? error.message : String(error)}`;
    }
  }
  return (
    <main>
      <h1 className="font-display text-4xl">Discovery</h1>
      <p className="mt-3 max-w-2xl text-sm text-ink/75">{health}</p>
      <p className="mt-3 max-w-2xl text-sm text-ink/75">
        The Python service in cinema/discovery reads the Internet Archive search API and drops any item whose licence URL is missing, non-commercial, or no-derivatives. It does not download video files and it does not bypass access controls.
      </p>
      <ul className="mt-6 space-y-3">
        {sample.map((item) => {
          const candidate = archiveCandidate(item);
          return (
            <li key={item.identifier} className="rounded-2xl border border-white/10 p-4 text-sm">
              <p className="font-semibold">{item.title}</p>
              <p className="text-ink/60">{item.licenseurl || "No licence URL"}</p>
              <p className="mt-1">{candidate ? `Accepted. Player: ${candidate.authorizedEmbedUrl}` : "Refused. No player URL is created."}</p>
            </li>
          );
        })}
      </ul>
    </main>
  );
}
