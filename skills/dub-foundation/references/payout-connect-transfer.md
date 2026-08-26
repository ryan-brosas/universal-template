<!-- capsule-v2 -->
# Stripe Connect transfer ladder — how do you fold a partner's processed payouts into one transfer without ever exceeding the original charge, and what happens on sub-minimum or disabled accounts?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What are the exact pre-transfer gates for a Connect payout, when is `source_transaction` omitted, and why?

## createStripeTransfer: processed+current fold → capability gate → fee-or-skip → guarded transfer
**Path/Symbol:** `apps/web/lib/partners/create-stripe-transfer.ts:createStripeTransfer` (:26-350); dispatcher `apps/web/app/(ee)/api/cron/payouts/send-stripe-payout/route.ts` (:32-65 picks connect vs stablecoin from the FIRST processing payout); idempotency key `apps/web/lib/payouts/create-payouts-idempotency-key.ts:6-27`.
**Signature:** `createStripeTransfer({ partnerId, invoiceId?, chargeId?, forceWithdrawal? })`.
**Data Shape:** two payout buckets merged oldest-id-first: `status:"processed" ∧ stripeTransferId:null ∧ method:"connect"` (stranded backlog) + `invoiceId ∧ status:"processing" ∧ method:"connect"` (current); constants MIN_WITHDRAWAL=$10, BELOW_MIN_FEE=$0.50, MIN_FORCE_WITHDRAWAL=$1 (`constants/payouts.ts:41-44`).

### Decisive source
```ts
if (!stripeConnectAccount.payouts_enabled ||
    !stripeConnectAccount.capabilities?.transfers ||
    stripeConnectAccount.capabilities.transfers === "inactive") {
  await prisma.partner.update({ where: { id: partner.id },
    data: { payoutsEnabledAt: null, defaultPayoutMethod: null } });
  await markPayoutsAsProcessed(currentInvoicePayouts);   // release the invoice hold
  ... forceWithdrawal ? throw : return; }
// Omit `source_transaction` if prior processed payouts exist to ensure this transfer
// never exceeds the original charge amount.
...(previouslyProcessedPayouts.length === 0 && chargeId && { source_transaction: chargeId }),
```
(:164-217)
```ts
const sortedPayoutIds = [...payoutIds].sort((a, b) => a.localeCompare(b));
const hash = createHash("sha256").update(sortedPayoutIds.join(",")).digest("hex").slice(0, 32);
return invoiceId ? `payouts-${invoiceId}-${partnerId}` : `payouts-${partnerId}-${hash}`;
```
(create-payouts-idempotency-key.ts :15-26)

**Flow:** load partner → no connectId/payoutsEnabled ⇒ warn+return (cron context) → fetch both buckets → total < $10: force ⇒ add $0.50 fee to be deducted (`finalTransferableAmount = total − withdrawalFee` :126-154), non-force ⇒ mark current payouts processed and skip the transfer entirely (money waits for the next batch) → retrieve account, dead account ⇒ clear payout fields + release holds → `transfer_group = last bucket's invoiceId` (comment :207-209: group may span multiple invoices) → create transfer with the deterministic idempotency key → stamp payouts `{stripeTransferId, status:"sent", paidAt}` → commissions→paid in 250-chunks with logged per-chunk failures → allSettled(activity-log + referral queue fan-out) → partner email.
**Invariant:** (1) source_transaction is attached ONLY when every transferred dollar belongs to the current charge — mixing stranded backlog under one charge's source would try to pull more than that charge ever held; (2) the deterministic key means ANY re-run of the same payout set returns Stripe's original transfer instead of duplicating money — payout-id ORDER must be canonicalized before hashing; (3) failed capability checks downgrade the partner (payoutsEnabledAt=null) rather than retrying forever; (4) below-minimum non-force is a DEFER (processed status), never a silent drop.
**Probe:** deterministic probe: `grep -n 'source_transaction: chargeId' apps/web/lib/partners/create-stripe-transfer.ts` = :216; `grep -c "status: \"sent\"" apps/web/lib/partners/create-stripe-transfer.ts` = 1. No upstream unit suite covers this file (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "createStripeTransfer", limit: 5 });
```

## Verdict
Adopt the two-bucket fold + charge-bounded source_transaction rule + content-addressed idempotency keys verbatim for any Stripe Connect-style rail. Adapt minimum/fee constants and the express-account capability checks. Omit the force-withdrawal surcharge branch unless you expose manual withdrawals.
