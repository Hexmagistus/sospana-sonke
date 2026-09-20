"use client";

import { WHATSAPP_CHANNEL_URL } from "@/lib/social";

function WhatsAppIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className={className}>
      <path d="M20.52 3.48A11.86 11.86 0 0 0 12.04 0C5.5 0 .2 5.3.2 11.84c0 2.09.55 4.13 1.59 5.93L0 24l6.4-1.68a11.8 11.8 0 0 0 5.64 1.44h.01c6.53 0 11.84-5.3 11.84-11.84 0-3.16-1.23-6.13-3.37-8.44ZM12.05 21.75h-.01a9.9 9.9 0 0 1-5.04-1.38l-.36-.21-3.8 1 1.01-3.7-.24-.38a9.9 9.9 0 0 1-1.52-5.24c0-5.47 4.45-9.92 9.93-9.92 2.65 0 5.14 1.03 7.01 2.91a9.85 9.85 0 0 1 2.9 7.02c0 5.47-4.45 9.9-9.88 9.9Zm5.44-7.42c-.3-.15-1.77-.87-2.04-.97-.27-.1-.47-.15-.67.15-.2.3-.77.97-.94 1.17-.17.2-.35.22-.65.07-.3-.15-1.26-.46-2.4-1.48-.89-.79-1.49-1.77-1.66-2.07-.17-.3-.02-.46.13-.61.14-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.08-.15-.67-1.62-.92-2.22-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.8.37-.27.3-1.04 1.02-1.04 2.48s1.07 2.88 1.22 3.08c.15.2 2.1 3.2 5.08 4.49.71.31 1.26.49 1.7.63.71.23 1.36.2 1.87.12.57-.08 1.77-.72 2.02-1.42.25-.7.25-1.29.17-1.42-.07-.13-.27-.2-.57-.35Z" />
    </svg>
  );
}

/** Opt-in link to the public Sospana Sonke WhatsApp channel. Following is one-way and
 * anonymous: no phone numbers are collected or shared, and we never message anyone. */
export function WhatsAppChannelButton({
  className = "",
  label = "Join our WhatsApp channel",
  source,
}: {
  className?: string;
  label?: string;
  /** Where the button sits (for readable analytics hooks later). */
  source?: string;
}) {
  return (
    <a
      href={WHATSAPP_CHANNEL_URL}
      target="_blank"
      rel="noopener noreferrer"
      data-source={source}
      className={`inline-flex items-center justify-center gap-2 rounded-xl bg-[#25D366] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#1ebe5b] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#25D366] focus-visible:ring-offset-2 ${className}`}
    >
      <WhatsAppIcon />
      {label}
    </a>
  );
}

/** Dashboard card: pitch + button. */
export function WhatsAppChannelCard() {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-[#25D366]/40 bg-[#25D366]/10 p-5 text-ss-text">
      <div className="min-w-0 flex-1">
        <p className="text-base font-semibold">Get new vacancies on WhatsApp</p>
        <p className="mt-1 text-sm text-ss-muted">
          Follow the Sospana Sonke channel for fresh openings, closing-date reminders and application tips.
          It&apos;s optional, free, and private — other followers can&apos;t see your number.
        </p>
      </div>
      <WhatsAppChannelButton source="dashboard" label="Follow the channel" />
    </div>
  );
}
