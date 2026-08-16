"use client";

import { useEffect, useState } from "react";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Alert, Spinner, Badge, Button } from "@/components/ui";
import type { Subscription } from "@/lib/types";

function SubscriptionInner() {
  const [sub, setSub] = useState<Subscription | null>(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState("");

  async function load() {
    setSub(await api.get<Subscription>("/subscription"));
  }
  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, []);

  async function checkout() {
    setBusy("checkout"); setErr("");
    try {
      const r = await api.post<{ authorization_url: string }>("/subscription/checkout");
      window.open(r.authorization_url, "_blank");
      setMsg("A checkout page has opened in a new tab. After paying, your subscription activates automatically.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Checkout failed");
    } finally { setBusy(""); }
  }

  async function mockPay() {
    setBusy("pay"); setErr("");
    try { await api.post("/subscription/mock-pay"); await load(); setMsg("Payment simulated — subscription active."); }
    catch (e) { setErr(e instanceof Error ? e.message : "Not available (mock only)"); }
    finally { setBusy(""); }
  }

  async function cancel() {
    setBusy("cancel"); setErr("");
    try { await api.post("/subscription/cancel"); await load(); setMsg("Cancellation scheduled at period end."); }
    catch (e) { setErr(e instanceof Error ? e.message : "Cancel failed"); }
    finally { setBusy(""); }
  }

  if (err && !sub) return <Alert kind="error">{err}</Alert>;
  if (!sub) return <Spinner />;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Subscription</h1>
      {msg && <Alert kind="success">{msg}</Alert>}
      {err && <Alert kind="error">{err}</Alert>}

      <Card>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-gray-500">Status</div>
            <div className="mt-1 flex items-center gap-2">
              <Badge>{sub.status}</Badge>
              {sub.has_access ? <span className="text-sm text-green-700">Active access</span> : <span className="text-sm text-red-600">No access</span>}
            </div>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold">R{sub.amount_zar}<span className="text-base font-normal text-gray-500">/mo</span></div>
            {sub.current_period_end && <div className="text-xs text-gray-400">Renews {new Date(sub.current_period_end).toLocaleDateString()}</div>}
            {sub.trial_end && sub.status === "TRIAL" && <div className="text-xs text-gray-400">Trial ends {new Date(sub.trial_end).toLocaleDateString()}</div>}
          </div>
        </div>
      </Card>

      <Card>
        <h2 className="mb-2 font-semibold">One subscription, everything included</h2>
        <ul className="mb-4 list-disc pl-5 text-sm text-gray-600">
          <li>Vacancy matching &amp; explanations</li>
          <li>Tailored CVs &amp; cover letters</li>
          <li>Application preparation &amp; tracking</li>
          <li>Candidate reports</li>
        </ul>
        <div className="flex flex-wrap gap-3">
          <Button onClick={checkout} disabled={!!busy}>{busy === "checkout" ? "Opening…" : "Subscribe / manage payment"}</Button>
          <Button variant="ghost" onClick={mockPay} disabled={!!busy}>{busy === "pay" ? "…" : "Simulate payment (dev)"}</Button>
          {sub.has_access && !sub.cancel_at_period_end && (
            <Button variant="danger" onClick={cancel} disabled={!!busy}>Cancel</Button>
          )}
        </div>
        {sub.cancel_at_period_end && <p className="mt-3 text-sm text-gray-500">Cancellation scheduled — access continues until the period ends.</p>}
      </Card>
    </div>
  );
}

export default function SubscriptionPage() {
  return (
    <Guard>
      <SubscriptionInner />
    </Guard>
  );
}
