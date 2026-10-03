import { safeHref, slotKeys, type PublicAd, type Side } from "./adSlots";

type SlotProps = { slotKey: string; ad?: PublicAd; onApply: (slotKey: string) => void };

/** One advertiser spot: an approved ad (labelled Sponsored) or an invitation to apply. */
export function AdSlot({ slotKey, ad, onApply }: SlotProps) {
  const href = ad ? safeHref(ad.website) : null;
  if (ad && href) {
    return (
      <li
        data-slot={slotKey}
        className="flex min-h-[4.25rem] min-w-0 flex-col justify-between rounded-lg border border-gold/50 bg-[#0a1a30] p-1.5 text-white"
      >
        <span className="text-[9px] font-bold uppercase tracking-wider text-[#ffe08a]">Sponsored</span>
        <a
          href={href}
          target="_blank"
          rel="sponsored noopener"
          className="min-w-0 break-words text-[11px] font-semibold leading-tight text-white underline-offset-2 hover:underline"
        >
          <span className="block truncate">{ad.business_name}</span>
          <span className="line-clamp-2 font-normal text-blue-100">{ad.ad_text}</span>
        </a>
      </li>
    );
  }
  return (
    <li
      data-slot={slotKey}
      className="flex min-h-[4.25rem] min-w-0 flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-gold/40 bg-[#0a1a30] p-1.5 text-center"
    >
      <span className="text-[11px] font-semibold text-blue-100">Your ad here</span>
      <button
        type="button"
        onClick={() => onApply(slotKey)}
        aria-label={`Apply for spot ${slotKey}`}
        className="rounded-full bg-gold px-2 py-0.5 text-[10px] font-bold text-navy hover:brightness-110"
      >
        Apply for this spot
      </button>
    </li>
  );
}

type ColumnProps = {
  side: Side;
  ads: ReadonlyArray<PublicAd>;
  onApply: (slotKey: string) => void;
};

/** A column of ten spots. Hidden below xl so small screens keep the original layout. */
export function AdColumn({ side, ads, onApply }: ColumnProps) {
  const bySlot = new Map(ads.map((a) => [a.slot_key, a]));
  return (
    <aside
      aria-label={`${side === "L" ? "Left" : "Right"} advertiser spots`}
      className="hidden xl:block"
    >
      <ul className="grid h-full grid-rows-10 gap-2">
        {slotKeys(side).map((k) => (
          <AdSlot key={k} slotKey={k} ad={bySlot.get(k)} onApply={onApply} />
        ))}
      </ul>
    </aside>
  );
}
