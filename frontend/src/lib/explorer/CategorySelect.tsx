"use client";

import { useId } from "react";

export type CategoryOption = { id: string; label: string; count: number | null };

/** Display text of one option: "Municipalities 262". */
export function categoryOptionText(o: CategoryOption): string {
  return o.count === null ? o.label : `${o.label} ${o.count.toLocaleString()}`;
}

type Props = {
  options: readonly CategoryOption[];
  value: string;
  onChange: (id: string) => void;
  /** Where the counts are for, e.g. "South Africa" or "all countries". */
  scope: string;
};

/** One category dropdown (native select: keyboard and mobile friendly). Counts are for the selected country. */
export function CategorySelect({ options, value, onChange, scope }: Props) {
  const id = useId();
  return (
    <div className="mx-auto flex w-full max-w-md flex-col items-stretch gap-1 pb-3 sm:flex-row sm:items-center sm:justify-center sm:gap-2">
      <label htmlFor={id} className="text-center text-[11px] font-bold uppercase tracking-wider text-blue-200 sm:text-left">
        Category
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-describedby={`${id}-hint`}
        className="min-w-0 flex-1 rounded-lg border border-white/20 bg-[#071528] px-3 py-2 text-sm font-semibold text-white focus:border-gold"
      >
        {options.map((o) => (
          <option key={o.id} value={o.id}>{categoryOptionText(o)}</option>
        ))}
      </select>
      <span id={`${id}-hint`} className="sr-only">Counts are for {scope}.</span>
    </div>
  );
}
