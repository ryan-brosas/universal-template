<!-- capsule-v2 -->
# PayPal payout success closure — invoice-id split, idempotent completion, and chunked commission payment

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** When PayPal reports a payout item succeeded, how does Dub close the loop idempotently across payout + hundreds of commissions?

## payoutsItemSucceeded
**Path/Symbol:** `apps/web/app/(ee)/api/paypal/webhook/payouts-item-succeeded.ts:payoutsItemSucceeded` (:7-104); envelope schema `apps/web/app/(ee)/api/paypal/webhook/utils.ts:payoutsItemSchema` (:3-23).
**Signature:** `payoutsItemSucceeded(event: any): Promise<void>` — zod-parses internally.
**Data Shape:** resource maps: `sender_batch_id` → Dub INVOICE id (may carry a `-suffix` from batch retries — split on first `-`), `payout_item.sender_item_id` → Dub PAYOUT id, `payout_item_id` → PayPal transfer id, `payout_item.receiver` → partner paypal email (logging only).

### Decisive source
```ts
let invoiceId = body.resource.sender_batch_id;
...
if (invoiceId.includes("-")) {
  invoiceId = invoiceId.split("-")[0];
}
```
(:10-17)

and

```ts
await prisma.payout.update({
  where: {
    id: payout.id,
  },
  data: {
    paypalTransferId: payoutItemId,
    status: "completed",
    paidAt: payout.paidAt ?? new Date(), // preserve the paidAt if it already exists
    failureReason: null,
  },
});
```
(:55-65)

**Flow:** parse envelope → split retry suffix off the batch/invoice id (pass-6's success path appends `-nanoid(7)` to make PayPal see a NEW batch id, so callbacks arrive with suffixed ids) → load payout by sender_item_id (missing ⇒ log + ACK) → ALREADY-completed ⇒ log + return (idempotency against redelivery) → stamp payout completed with transferId + preserved-paidAt + CLEARED failureReason → chunk commission ids by 250 and updateMany each to status "paid", accumulating counts, per-chunk errors logged-not-thrown → waitUntil(trackCommissionStatusUpdate) for activity-log fan-out.
**Invariant:** the paidAt preserve (`?? new Date()`) matters because the charge-side flow may have stamped paidAt before PayPal's callback arrived; clearing failureReason is part of the completion contract (a previously-failed-then-retried payout must not keep its stale error); commission update failures NEVER fail the webhook (already 2xx-bound) — they log with mention:true for humans.
**Probe:** deterministic probes (repo root): `grep -n 'chunk(commissionIds, 250)' "apps/web/app/(ee)/api/paypal/webhook/payouts-item-succeeded.ts"` → :70; `grep -n 'paidAt ?? new Date()' ...` → :62; `grep -c 'status: "paid"' ...` → 1; `grep -n 'sender_batch_id' "apps/web/app/(ee)/api/paypal/webhook/utils.ts"` → :6; `grep -n 'invoiceId.split' ...succeeded.ts` → :16.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "payoutsItemSucceeded", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the id-split lookup, completed-idempotency gate, paidAt preservation, and chunked best-effort commission flip. Adapt ORM/chunk util. Omit nothing.
