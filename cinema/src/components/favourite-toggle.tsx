"use client";

import { useEffect, useState } from "react";
import { browserLibrary } from "@/lib/local-library";

export function FavouriteToggle({ slug, title }: { slug: string; title: string }) {
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    setSaved(browserLibrary().read().favourites.includes(slug));
  }, [slug]);
  const label = saved ? `Remove ${title} from favourites` : `Save ${title} on this device`;
  return (
    <button
      type="button"
      aria-pressed={saved}
      aria-label={label}
      className="rounded-full border border-white/20 px-4 py-3 text-sm"
      onClick={() => {
        const next = browserLibrary().toggleFavourite(slug);
        setSaved(next.favourites.includes(slug));
      }}
    >
      {saved ? "Saved on this device" : "Save on this device"}
    </button>
  );
}
