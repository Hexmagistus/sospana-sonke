import { DemoBanner, SiteFooter, SiteHeader } from "@/components/chrome";
import { getPublicCatalog } from "@/lib/public-catalog";

export const dynamic = "force-dynamic";

export default async function SiteLayout({ children }: { children: React.ReactNode }) {
  const catalog = await getPublicCatalog();
  return (
    <>
      <SiteHeader />
      <DemoBanner warning={catalog.warning} />
      <div id="content" className="mx-auto max-w-6xl px-4 py-6">
        {children}
      </div>
      <SiteFooter />
    </>
  );
}
