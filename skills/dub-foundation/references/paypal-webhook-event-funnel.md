<!-- capsule-v2 -->
# PayPal payout webhook dispatch — the 9-event funnel collapsing to two handlers

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** Which PayPal payout events does the receiver accept, and how do eight failure flavors become one handler?

## relevantEvents set + switch fan-in
**Path/Symbol:** `apps/web/app/(ee)/api/paypal/webhook/route.ts:POST` (:20-72).
**Signature:** `POST(req: Request): Promise<Response>` — raw-body-first, returns "OK" | 400 on handler error | 200 "Unsupported event, skipping..." for unlistened types.
**Data Shape:** `relevantEvents: Set<string>` of exactly 9 `PAYMENT.PAYOUTS-ITEM.*` types (SUCCEEDED + BLOCKED/CANCELED/DENIED/FAILED/HELD/REFUNDED/RETURNED/UNCLAIMED).

### Decisive source
```ts
switch (body.event_type) {
  case "PAYMENT.PAYOUTS-ITEM.SUCCEEDED":
    await payoutsItemSucceeded(body);
    break;
  case "PAYMENT.PAYOUTS-ITEM.BLOCKED":
  case "PAYMENT.PAYOUTS-ITEM.CANCELED":
  case "PAYMENT.PAYOUTS-ITEM.DENIED":
  case "PAYMENT.PAYOUTS-ITEM.FAILED":
  case "PAYMENT.PAYOUTS-ITEM.HELD":
  case "PAYMENT.PAYOUTS-ITEM.REFUNDED":
  case "PAYMENT.PAYOUTS-ITEM.RETURNED":
  case "PAYMENT.PAYOUTS-ITEM.UNCLAIMED":
    await payoutsItemFailed(body);
    break;
}
```
(route.ts :43-57)

**Flow:** read RAW body text → verify signature BEFORE JSON.parse → unknown type ⇒ early 200 with skip message (PayPal retries only non-2xx, so unsupported events must ACK) → dispatch: SUCCEEDED ⇒ payoutsItemSucceeded; ALL EIGHT other listed types ⇒ payoutsItemFailed (which internally decides whether they map to a Dub "failed" status) → any thrown error ⇒ log + 400 response so PayPal redelivers.
**Invariant:** unsupported events return 200 BY DESIGN — failing them would loop PayPal redelivery forever on event types the integration will never handle; the 8→1 collapse means HELD or UNCLAIMED (not strictly failures) flow through the failed-handler's own mapping gate, keeping route-level logic minimal; raw-text-before-parse ordering is shared with the HMAC-style receivers (`webhook-signature` capsule) but PayPal's scheme is cert-based.
**Probe:** deterministic probes (repo root): `grep -c 'PAYMENT.PAYOUTS-ITEM' "apps/web/app/(ee)/api/paypal/webhook/route.ts"` → 18 (9 in Set ×2: declaration+switch); `grep -n 'relevantEvents' "apps/web/app/(ee)/api/paypal/webhook/route.ts"` → :6/:36; `grep -c 'payoutsItemFailed(body)' "apps/web/app/(ee)/api/paypal/webhook/route.ts"` → 1; `grep -n 'Unsupported event' "apps/web/app/(ee)/api/paypal/webhook/route.ts"` → :38.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "payoutsItemFailed", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt verify→parse→set-gate→fan-in-switch with 200-ACK for unknown events and 400-on-error redelivery semantics. Adapt event vocabulary. Omit nothing.
