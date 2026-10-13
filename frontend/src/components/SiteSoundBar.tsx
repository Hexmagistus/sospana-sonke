"use client";

import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { isExplorerPath } from "@/lib/explorer/explorerPaths";
import { SoundControls } from "@/components/SoundControls";

/**
 * Logged-out pages other than the homepage have no site header of their own.
 * Explorer pages hide that header on a wide screen, so the same controls sit here.
 */
export function SiteSoundBar() {
  const pathname = usePathname();
  const { user, loading } = useAuth();
  if (pathname === "/" || loading) return null;
  if (user && !isExplorerPath(pathname)) return null;
  const desktopOnly = Boolean(user && isExplorerPath(pathname));
  return (
    <div className={`mx-auto max-w-6xl justify-end px-4 pt-3 ${desktopOnly ? "hidden lg:flex" : "flex"}`}>
      <SoundControls />
    </div>
  );
}
