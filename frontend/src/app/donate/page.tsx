"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, Button, Input, Textarea, Field, Alert } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { CircuitOverlay, GlowFrame } from "@/components/HighTech";

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
  const [cash, setCash] = useState<{ ready: boolean; number: string | null; reference: string } | null>(null);
  const [copied, setCopied] = useState("");

  useEffect(() => {
    api.get<{ ready: boolean; number: string | null; reference: string }>("/donations/cashsend")
      .then(setCash)
      .catch(() => setCash({ ready: false, number: null, reference: "Sospana Sonke donation" }));
  }, []);

  async function copy(label: string, value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(label);
    } catch {
      setCopied("");
    }
  }

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
    <div className="relative mx-auto max-w-xl space-y-5">
      <CircuitOverlay className="-z-10 opacity-70" opacity={0.1} stroke="#0b1f3a" dotColor="#f5b301" />
      <div>
        <h1 className="text-2xl font-bold text-ss-text">Help keep Sospana Sonke free</h1>
        <p className="mt-1.5 text-sm text-ss-muted">
          Sospana Sonke doesn&apos;t charge jobseekers anything. If it&apos;s helped you, a small
          voluntary donation helps cover hosting. It does not unlock features, and it is not a payment
          for a job. We never see or store your card or bank details.
        </p>
      </div>

      <GlowFrame>
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
                      : "border-ss-border text-ss-text hover:border-brand"
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
                    : "border-ss-border text-ss-text hover:border-brand"
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

          <Button type="submit" size="lg" loading={loading} disabled={!canSubmit} glow className="w-full">
            Donate R{Number.isFinite(effectiveAmount) && effectiveAmount > 0 ? Math.round(effectiveAmount) : "…"} →
          </Button>
          <p className="text-center text-xs text-ss-muted">
            Card checkout opens on the payment provider&apos;s page (Paystack when that is switched on).
            This server does not collect the card number. If card payments are not live yet, the button
            will say so — cash send below is the other option.
          </p>
        </form>
      </Card>
      </GlowFrame>

      <Card>
        <h2 className="mb-2 font-semibold text-ss-text">Cash send from a South African bank app</h2>
        <p className="text-sm text-ss-muted">
          Open your own bank app and use FNB eWallet, ABSA CashSend, Standard Bank Instant Money,
          Nedbank Send-iMali, or Capitec cash send. You pay inside the bank app. We only show a
          cellphone number, and only when it has been configured.
        </p>
        {cash === null && <p className="mt-3 text-sm text-ss-muted">Checking whether cash send is published…</p>}
        {cash && !cash.ready && (
          <Alert kind="info">
            Cash send is coming soon — the recipient number isn&apos;t published yet. Card checkout above
            still works once a payment provider is switched on. The kettle&apos;s on either way.
          </Alert>
        )}
        {cash?.ready && cash.number && (
          <div className="mt-3 space-y-3">
            <p className="text-sm text-ss-text">
              Send to <span className="font-semibold">{cash.number}</span>. Reference:{" "}
              <span className="font-semibold">{cash.reference}</span>.
            </p>
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="secondary" onClick={() => copy("number", cash.number || "")}>
                {copied === "number" ? "Number copied" : "Copy number"}
              </Button>
              <Button type="button" variant="secondary" onClick={() => copy("reference", cash.reference)}>
                {copied === "reference" ? "Reference copied" : "Copy reference"}
              </Button>
            </div>
            {copied && (
              <p className="text-sm text-ss-text" role="status">
                Copied. Open your bank app, choose cash send, and paste. We don&apos;t get a receipt from
                the bank, so this screen cannot confirm the money arrived.
              </p>
            )}
          </div>
        )}
      </Card>

      <p className="text-center text-sm">
        <Link href="/companies" className="text-brand hover:underline">← Back to Sospana Sonke</Link>
      </p>
    </div>
  );
}
