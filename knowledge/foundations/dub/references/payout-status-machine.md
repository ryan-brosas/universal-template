<!-- capsule-v2 -->
# Payout status state machine — what is the full legal transition graph for a Payout row, and which writer owns each edge?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** Can you draw the complete payout status lifecycle across aggregation, invoicing, the four rails, and the webhook closures — without inventing transitions?

## Status map assembled from all writers
**Path/Symbol:** writers: aggregate cron (`aggregate-due-commissions/process/route.ts:272-335`), processPayouts (:73-119), markPayoutsAsProcessed (`lib/payouts/mark-payouts-as-processed.ts:9-19` — `processed`+paidAt), createStripeTransfer (:258-270 — `sent`), sendPaypalPayouts (:68-74 — `sent`), createStablecoinPayout (:294-306 — `sent`), sendTremendousPayouts (:209-217 — `completed` direct), payout-failed/paid routes (`failed`/`completed`), balance-available re-tag, retry action (`failed→processing`).
**Signature:** MUTABLE_PAYOUT_STATUSES = `["pending","canceled"]` guards every aggregation-side write; terminal statuses are keyed by provider ids (stripeTransferId / stripePayoutId / tremendousOrderId / paypalTransferId).
**Data Shape:** statuses observed in code: pending → processed → processing → sent → completed; side exits: canceled (clawbacks/refunds), failed (+failureReason).

### Decisive source
```ts
// markPayoutsAsProcessed — the universal "release the hold" primitive
const { count } = await prisma.payout.updateMany({
  where: { id: { in: payouts.map((p) => p.id) } },
  data: { status: "processed", paidAt: new Date() } });
```
(mark-payouts-as-processed.ts :9-19)
```ts
// eligibility filter admits ONLY pending + invoiceId:null rows to an invoice
status: "pending", invoiceId: null, amount: { gte: program.minPayoutAmount }
```
(payout-eligibility-filter.ts :11-20)

**Flow (edges):** commissions claim ⇒ payout created `pending` (amount 0) → amount filled while pending → invoice confirm flips selected pendings ⇒ `processing` (+invoiceId, mode, initiatedAt) → rail success ⇒ `sent` (connect/paypal/stablecoin; +provider id +paidAt) OR straight to `completed` (tremendous, where delivery IS fulfillment) → Stripe auto-withdrawal closes connect payouts via payout.paid ⇒ `completed` (+traceId); payout.failed ⇒ `failed` (+failureReason) → partner retry flips `failed⇒processing` (guarded count-checked) and failure during retry reverts to `failed`; sub-minimum or dead-account paths return processing rows to `processed` (deferred, no invoice yet on next cycle... they keep invoiceId but leave the money unmoved). `canceled` exists as a mutable clawback state admitted by MUTABLE_PAYOUT_STATUSES.
**Invariant:** (1) `processed` means "claimable but not on an invoice" AND "released from a failed attempt" — context comes from invoiceId nullness, so porters must NOT treat it as terminal; (2) only pending/canceled are mutation-eligible for AGGREGATION writes; processing+ rows are owned by rails/webhooks; (3) every terminal write also stamps paidAt and a provider id, making reconciliation with provider dashboards possible row-by-row; (4) tremendous skips `sent` because its order completion is synchronous.
**Probe:** deterministic probe: `grep -rhoE 'status: "(pending|processing|processed|sent|completed|failed|canceled)"' apps/web/lib apps/web/app --include='*.ts' | sort | uniq -c` shows every writer listed above; `grep -c '"processed"' apps/web/lib/payouts/mark-payouts-as-processed.ts` = 1. No upstream unit suite covers the whole graph (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "markPayoutsAsProcessed", limit: 5 });
```

## Verdict
Adopt the transition graph as the integration test checklist when porting ANY of the rails — partial ports that skip the release-to-processed path deadlock partners' money. Adapt status names. Omit nothing; this capsule is the map tying the other payout capsules together.
