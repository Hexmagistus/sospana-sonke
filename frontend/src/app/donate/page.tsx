"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, Button, Input, Textarea, Field, Alert } from "@/components/ui";
import { api, ApiError } from "@/lib/api";

const PRESET_AMOUNTS = [20, 50, 100] as const;

export default function DonatePage() {
  const [amount, setAmount] = useState<number>(50);
  const [customAmount, setCustomAmount] = useState("");
  const [usingCustom, setUsingCustom] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const effectiveAmount = usingCustom ? Number(customAmount) : amount;
  const canSubmit =
    effectiveAmount >= 5 && effectiveAmount <= 20000 && /\S+@\S+\.\S+/.test(email) && !loading;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!canSubmit) return;
    setLoading(true);
    try {
      const res = await api.post<{ authorization_url: string; reference: string }>(
        "/donations/checkout",
        {
          amount_zar: Math.round(effectiveAmount),
          email,
          name: name || undefined,
          message: message || undefined,
        }
      );
      if (res.authorization_url) {
        window.location.href = res.authorization_url;
      } else {
        setError("Something went wrong starting checkout. Please try again.");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-navy">Help keep Sospana Sonke free</h1>
        <p className="mt-1.5 text-sm text-gray-600">
          Sospana Sonke doesn&apos;t charge jobseekers anything — every feature is free for everyone
          across Southern Africa. If it&apos;s helped you, a small voluntary donation helps cover the
          hosting and running costs so it can stay that way for the next person.
        </p>
      </div>

      <Card>
        <form onSubmit={submit} className="space-y-4">
          <Field label="Choose an amount (ZAR)">
            <div className="grid grid-cols-4 gap-2">
              {PRESET_AMOUNTS.map((a) => (
                <button
                  type="button"
                  key={a}
                  onClick={() => {
                    setUsingCustom(false);
                    setAmount(a);
                  }}
                  className={`rounded-lg border px-2 py-2.5 text-sm font-semibold transition ${
                    !usingCustom && amount === a
                      ? "border-brand bg-brand/10 text-brand-dark"
                      : "border-gray-300 text-gray-700 hover:border-brand"
                  }`}
                >
                  R{a}
                </button>
              ))}
              <button
                type="button"
                onClick={() => setUsingCustom(true)}
                className={`rounded-lg border px-2 py-2.5 text-sm font-semibold transition ${
                  usingCustom
                    ? "border-brand bg-brand/10 text-brand-dark"
                    : "border-gray-300 text-gray-700 hover:border-brand"
                }`}
              >
                Other
              </button>
            </div>
            {usingCustom && (
              <div className="mt-2">
                <Input
                  type="number"
                  min={5}
                  max={20000}
                  step={1}
                  placeholder="Enter an amount, e.g. 250"
                  value={customAmount}
                  onChange={(e) => setCustomAmount(e.target.value)}
                />
              </div>
            )}
          </Field>

          <Field label="Email" hint="for your receipt">
            <Input
              type="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </Field>

          <Field label="Name" hint="optional">
            <Input
              placeholder="Anonymous"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </Field>

          <Field label="Message" hint="optional">
            <Textarea
              rows={2}
              placeholder="Say something nice (optional)"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
            />
          </Field>

          {error && <Alert kind="error">{error}</Alert>}

          <Button type="submit" size="lg" loading={loading} disabled={!canSubmit} className="w-full">
            Donate R{Number.isFinite(effectiveAmount) && effectiveAmount > 0 ? Math.round(effectiveAmount) : "…"} →
          </Button>
          <p className="text-center text-xs text-gray-400">
            Secure card checkout via Paystack. Donations are voluntary and non-refundable, and don&apos;t
            unlock any extra features — the app is free either way.
          </p>
        </form>
      </Card>

      <Card>
        <h2 className="mb-2 font-semibold text-navy">Prefer a direct bank transfer?</h2>
        <p className="text-sm text-gray-600">
          You&apos;re welcome to send a donation straight to the project&apos;s bank account instead:
        </p>
        <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm text-gray-700">
          <dt className="font-medium text-gray-500">Bank</dt>
          <dd>Capitec Bank</dd>
          <dt className="font-medium text-gray-500">Account number</dt>
          <dd>2581657193</dd>
          <dt className="font-medium text-gray-500">SWIFT/BIC</dt>
          <dd>CABLZAJJ</dd>
        </dl>
        <p className="mt-2 text-xs text-gray-400">
          Please use &quot;Sospana Sonke donation&quot; as your payment reference.
        </p>
      </Card>

      <p className="text-center text-sm">
        <Link href="/companies" className="text-brand hover:underline">← Back to Sospana Sonke</Link>
      </p>
    </div>
  );
}
