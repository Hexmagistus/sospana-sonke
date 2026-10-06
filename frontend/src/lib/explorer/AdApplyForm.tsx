"use client";

import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import {
  AD_TEXT_MAX, EMPTY_FORM, LOGIN_SLOT_KEYS, MAX_DAYS, MIN_NOTE, MIN_USD_PER_DAY, NO_PAYMENT_NOTE, SLOT_LABELS,
  isLoginSlotKey, toPayload, totalUsd, validateAdForm, type AdErrors, type AdForm,
} from "./adSlots";

export type Receipt = { id: string; status: string; total_usd: string; message: string };

type FormProps = {
  slotKey: string | null;
  onClose: () => void;
  /** Start with these values (tests). */
  initial?: AdForm;
  /** Sends the application; the dialog passes the real API call. */
  submit: (payload: ReturnType<typeof toPayload>) => Promise<Receipt>;
};

function serverMessage(e: unknown): string {
  const raw = e instanceof Error ? e.message : "";
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      const msgs = parsed.map((d) => (d && typeof d.msg === "string" ? d.msg.replace(/^Value error, /, "") : "")).filter(Boolean);
      if (msgs.length) return msgs.join(" ");
    }
  } catch { /* plain text */ }
  return raw || "Something went wrong. Please try again.";
}

const inputCls =
  "mt-1 w-full rounded-lg border border-ss-border bg-ss-surface px-3 py-2 text-sm text-ss-text placeholder:text-ss-muted focus:border-gold focus:outline-none focus:ring-2 focus:ring-gold/40";

/** Application form for one advertiser spot. Nothing is charged and no email is sent. */
export function AdApplyForm({ slotKey, onClose, initial, submit }: FormProps) {
  const [f, setF] = useState<AdForm>(initial ?? EMPTY_FORM);
  const [errors, setErrors] = useState<AdErrors>({});
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  // Which of the four login-page spots; "" = any free spot.
  const [spot, setSpot] = useState<string>(isLoginSlotKey(slotKey) ? slotKey : "");
  const uid = useId();
  const set = (k: keyof AdForm) => (e: { target: { value: string } }) => setF((p) => ({ ...p, [k]: e.target.value }));
  const total = totalUsd(f);

  async function onSubmit(ev: FormEvent) {
    ev.preventDefault();
    const found = validateAdForm(f);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    setBusy(true);
    setFailure("");
    try {
      const body = toPayload(f, spot || null);
      setReceipt(await submit(body));
    } catch (e) {
      setFailure(serverMessage(e));
    } finally {
      setBusy(false);
    }
  }

  if (receipt) {
    return (
      <div className="space-y-3" role="status">
        <p className="text-base font-bold text-ss-text">Application received</p>
        <p className="text-sm text-ss-text">{receipt.message}</p>
        <button type="button" onClick={onClose} className="rounded-full bg-gold px-4 py-1.5 text-sm font-bold text-navy hover:brightness-110">
          Close
        </button>
      </div>
    );
  }

  const field = (k: keyof AdForm, label: string, extra: Record<string, unknown> = {}, hint?: string) => (
    <div>
      <label htmlFor={`${uid}-${k}`} className="block text-sm font-semibold text-ss-text">{label}</label>
      <input
        id={`${uid}-${k}`}
        value={f[k]}
        onChange={set(k)}
        aria-invalid={errors[k] ? true : undefined}
        aria-describedby={errors[k] ? `${uid}-${k}-err` : undefined}
        className={inputCls}
        {...extra}
      />
      {hint && !errors[k] && <p className="mt-0.5 text-xs text-ss-muted">{hint}</p>}
      {errors[k] && <p id={`${uid}-${k}-err`} className="mt-0.5 text-xs font-semibold text-red-600" role="alert">{errors[k]}</p>}
    </div>
  );

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-3">
      <p className="text-xs text-ss-muted">
        Ads appear on the sign-in page, in one of four spots. {MIN_NOTE}
      </p>
      <div>
        <label htmlFor={`${uid}-spot`} className="block text-sm font-semibold text-ss-text">Spot</label>
        <select id={`${uid}-spot`} value={spot} onChange={(e) => setSpot(e.target.value)} className={inputCls}>
          <option value="">Any free spot</option>
          {LOGIN_SLOT_KEYS.map((k) => (
            <option key={k} value={k}>{SLOT_LABELS[k]}</option>
          ))}
        </select>
      </div>
      {field("businessName", "Business name", { maxLength: 120, autoComplete: "organization" })}
      {field("email", "Contact email", { type: "email", maxLength: 254, autoComplete: "email" })}
      {field("website", "Website", { type: "text", inputMode: "url", maxLength: 500, placeholder: "https://example.com" })}
      {field("adText", "Short ad text", { maxLength: AD_TEXT_MAX }, `${f.adText.length}/${AD_TEXT_MAX} characters`)}
      <div className="grid grid-cols-2 gap-3">
        {field("amount", "Amount per day (USD)", { type: "number", min: MIN_USD_PER_DAY, step: "0.01", inputMode: "decimal" }, `At least $${MIN_USD_PER_DAY}/day.`)}
        {field("days", "Number of days", { type: "number", min: 1, max: MAX_DAYS, step: 1, inputMode: "numeric" })}
      </div>
      {total !== null && <p className="text-sm font-semibold text-ss-text">Total you would give: ${total.toFixed(2)}</p>}
      <p className="rounded-lg border border-gold/50 bg-gold/10 p-2 text-xs text-ss-text">{NO_PAYMENT_NOTE} We do not publish anything until an administrator approves it.</p>
      {failure && <p className="text-sm font-semibold text-red-600" role="alert">{failure}</p>}
      <div className="flex items-center justify-end gap-2">
        <button type="button" onClick={onClose} className="rounded-full px-4 py-1.5 text-sm font-semibold text-ss-muted hover:text-ss-text">Cancel</button>
        <button type="submit" disabled={busy} className="rounded-full bg-gold px-4 py-1.5 text-sm font-bold text-navy hover:brightness-110 disabled:opacity-60">
          {busy ? "Sending…" : "Send application"}
        </button>
      </div>
    </form>
  );
}

