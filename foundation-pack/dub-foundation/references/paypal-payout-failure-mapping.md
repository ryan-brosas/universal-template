<!-- capsule-v2 -->
# PayPal payout failure mapping — five-of-eight events fail, three only record, email only on real failure

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** Of PayPal's eight non-success payout-item events, which flip the payout to failed and which must NOT notify the partner?

## PAYPAL_TO_DUB_STATUS gate + failureReason capture
**Path/Symbol:** `apps/web/app/(ee)/api/paypal/webhook/payouts-item-failed.ts:payoutsItemFailed` (:14-91).
**Signature:** `payoutsItemFailed(event: any): Promise<void>`.
**Data Shape:** map covers BLOCKED/DENIED/FAILED/REFUNDED/RETURNED ⇒ "failed"; HELD/CANCELED/UNCLAIMED are absent ⇒ `payoutStatus: "failed" | undefined` = undefined; `resource.errors.message` (nullish) → failureReason.

### Decisive source
```ts
const PAYPAL_TO_DUB_STATUS = {
  "PAYMENT.PAYOUTS-ITEM.BLOCKED": "failed",
  "PAYMENT.PAYOUTS-ITEM.DENIED": "failed",
  "PAYMENT.PAYOUTS-ITEM.FAILED": "failed",
  "PAYMENT.PAYOUTS-ITEM.REFUNDED": "failed",
  "PAYMENT.PAYOUTS-ITEM.RETURNED": "failed",
};
```
(:6-12)

and

```ts
if (payoutStatus !== "failed") {
  // we only send emails for failed payouts
  console.log(
    `Paypal payout status changed to ${body.event_type} for invoice ${invoiceId} and partner ${paypalEmail}. This is not a failure event, skipping email send...`,
  );
  return;
}
```
(:58-64)

**Flow:** parse → split retry suffix off invoice id → load payout by sender_item_id (missing ⇒ log + ACK) → map event type to Dub status → update payout row with transferId + mapped status + errors.message regardless of flavor → undefined-mapped types (HELD/CANCELED/UNCLAIMED) return BEFORE any email → real failures require partner.email present, then send PartnerPaypalPayoutFailed notification with amount + failureReason.
**Invariant:** every event still writes paypalTransferId even when it doesn't map to failed — the transfer-id ledger updates on ANY callback; CANCELED being excluded from the failed map is deliberate (a canceled-before-send payout never left, so no alarming email); the email path reads `payout.partner.paypalEmail!` with non-null assertion guarded by the earlier partner.email presence check.
**Probe:** deterministic probes (repo root): `grep -n 'PAYPAL_TO_DUB_STATUS' "apps/web/app/(ee)/api/paypal/webhook/payouts-item-failed.ts"` → :6/:44; `grep -c '"failed"' "apps/web/app/(ee)/api/paypal/webhook/payouts-item-failed.ts"` → 7 (5 map rows + type annotation + comparison); `grep -n 'payoutStatus !== "failed"' ...` → :58; `grep -n 'invoiceId.split' ...` → :23; `grep -n 'errors?.message' ...` → :45.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "payoutsItemFailed", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the explicit 5-of-8 failed-map with write-through-transferId for all flavors and the email-only-on-failed gate. Adapt status enum/email transport. Omit nothing.
