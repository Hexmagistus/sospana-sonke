"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { browserLibrary, type Progress } from "@/lib/local-library";
import { useI18n } from "./i18n-provider";

export function ContinueRow() {
  const { t } = useI18n();
  const [items, setItems] = useState<Progress[]>([]);
  useEffect(() => setItems(browserLibrary().read().progress), []);
  if (items.length === 0) return null;
  return (
    <section className="mt-8" data-testid="continue-watching">
      <h2 className="font-display text-2xl">{t("library.continue")}</h2>
      <div className="mt-3 flex flex-wrap gap-3">
        {items.map((item) => (
          <Link key={item.slug} href={`/watch/${item.slug}`} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm">
            <span className="block font-semibold">{item.title}</span>
            <span className="text-ink/60">
              {item.player === "embed" ? "Opens again from the start" : `${Math.floor(item.position)}s saved`}
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
