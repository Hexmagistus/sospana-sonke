import { safeHref, slotKeys, type PublicAd, type Side } from "./adSlots";

type SlotProps = { slotKey: string; ad?: PublicAd; onApply: (slotKey: string) => void };

/** One advertiser spot: an approved ad (labelled Sponsored) or an invitation to advertise. */
export function AdSlot({ slotKey, ad, onApply }: SlotProps) {
  const href = ad ? safeHref(ad.website) : null;
  if (ad && href) {
    return (
      <li
        data-slot={slotKey}
        className="flex min-h-[6.5rem] min-w-0 flex-col justify-between gap-1 rounded-xl border border-gold/60 bg-ss-surface p-3 text-ss-text shadow-sm"
      >
        <span className="text-xs font-bold uppercase tracking-wider text-ss-primary">Sponsored</span>
        <a
          href={href}
          target="_blank"
          rel="sponsored noopener"
          className="min-w-0 break-words text-sm font-semibold leading-snug text-ss-text underline-offset-2 hover:underline"
        >
          <span className="block truncate">{ad.business_name}</span>
          <span className="line-clamp-2 font-normal text-ss-muted">{ad.ad_text}</span>
        </a>
      </li>
    );
  }
  return (
    <li
      data-slot={slotKey}
      className="flex min-h-[6.5rem] min-w-0 flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-gold/60 bg-ss-surface p-3 text-center shadow-sm"
    >
      <span className="text-sm font-semibold text-ss-text">Advertise here</span>
      <button
        type="button"
        onClick={() => onApply(slotKey)}
        aria-label={`Advertise here: apply for spot ${slotKey}`}
        className="min-h-10 rounded-full bg-gold px-3 py-1 text-sm font-bold text-navy hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-navy"
      >
        Apply for this spot
      </button>
    </li>
  );
}

type RailProps = {
  side: Side;
  ads: ReadonlyArray<PublicAd>;
  onApply: (slotKey: string) => void;
  className?: string;
};

/**
 * Two of the four login-page spots. On wide screens (xl) the login page puts one rail each
 * side of the form; below xl both rails follow the form in the page flow (form first),
 * two spots side by side from 400px and one per row on the narrowest phones.
 */
export function LoginAdRail({ side, ads, onApply, className = "" }: RailProps) {
  const bySlot = new Map(ads.map((a) => [a.slot_key, a]));
  return (
    <aside aria-label={`Sponsored spots (${side})`} data-ad-rail={side} className={`min-w-0 ${className}`}>
      <ul className="grid grid-cols-1 gap-3 min-[400px]:grid-cols-2 xl:grid-cols-1 xl:gap-4">
        {slotKeys(side).map((k) => (
          <AdSlot key={k} slotKey={k} ad={bySlot.get(k)} onApply={onApply} />
        ))}
      </ul>
    </aside>
  );
}
