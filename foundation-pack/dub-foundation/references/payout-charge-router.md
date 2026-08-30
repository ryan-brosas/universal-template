<!-- capsule-v2 -->
# Charge-succeeded payout router — when invoice funds settle, in what order do the four payout rails fire, and why do card charges gate three of them?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** After a program's invoice charge succeeds, which payout methods can move money immediately and which must wait for balance settlement — and how is the wait implemented?

## charge-succeeded route: method backfill → settlement gate → allSettled rail fan-out
**Path/Symbol:** `apps/web/app/(ee)/api/cron/payouts/charge-succeeded/route.ts:POST` (:24-136); `apps/web/app/(ee)/api/cron/payouts/charge-succeeded/utils.ts:getFundSettlementTiming` (:68-113) + `scheduleDelayedPayouts` (:26-52); per-rail queue siblings `queue-stripe-payouts.ts`, `queue-tremendous-payouts.ts`, `send-paypal-payouts.ts`, `queue-external-payouts.ts`.
**Signature:** `POST {invoiceId}` via QStash (signature-verified, `maxDuration=600`); rails receive `invoice` + optional `fundsAvailable`.
**Data Shape:** FundSettlementTiming = `{fundsAvailable:true} | {fundsAvailable:false, scheduledAt:Date}`; post-settlement methods = `[stablecoin, paypal, tremendous]` (:77-81).

### Decisive source
```ts
// Set the method for each payout in the invoice to the corresponding partner's default payout method
await prisma.$executeRaw`
  UPDATE Payout p INNER JOIN Partner pn ON p.partnerId = pn.id
  SET p.method = pn.defaultPayoutMethod
  WHERE p.invoiceId = ${invoice.id}
    AND pn.defaultPayoutMethod IS NOT NULL AND p.status = 'processing'`;
// ...
if (!fundSettlementTiming.fundsAvailable) {
  fundsAvailable = false;
  if (postSettlementPayoutsCount > 0)
    await scheduleDelayedPayouts({ invoice, executeAt: fundSettlementTiming.scheduledAt });
}
await Promise.allSettled([
  queueStripePayouts({ invoice, fundsAvailable }),          // connect always; stablecoin only when funded
  ...(fundsAvailable ? [ sendPaypalPayouts({ invoice }),
                         queueTremendousPayouts({ invoice }) ] : []),
  queueExternalPayouts(invoice),                            // webhook rail ignores funds
]);
```
(:59-123)

```ts
const availableOnMs = balanceTransaction.available_on * 1000;
if (availableOnMs <= now) return { fundsAvailable: true };
const scheduledAt = new Date(availableOnMs + 15 * 60 * 1000);   // +15 min buffer
```
(utils.ts :96-108; missing balance transaction ⇒ retry in 1 hour :84-91)

```ts
delay: delaySeconds + 5 * 60,                    // 5 minutes buffer for card settlement
deduplicationId: `retry-delayed-payouts-${invoice.id}`,   // dedup window is 10 minutes
flowControl: { key: invoice.id, parallelism: 1 },
```
(utils.ts :33-42 — re-publishes to THIS SAME route, so the whole router reruns after settlement)

**Flow:** QStash delivers charge-succeeded → raw UPDATE stamps each processing payout with the partner's default method → card invoices check Stripe `balanceTransactions.list(source=chargeId)`: unavailable ⇒ schedule a self-republish at available_on+15min (+5min extra delay, dedup'd, parallelism 1) → fan out rails under allSettled. Stripe rail pre-funds Dub's financial account for stablecoin (`sum(amount) + count×$0.50 fixed fee`, only amounts ≥ MIN_WITHDRAWAL_AMOUNT_CENTS $10 — sub-minimum payouts get marked processed for later manual force-withdrawal :44-70 of queue-stripe-payouts) then enqueues per-partner jobs `deduplicationId ${invoiceId}-${partnerId}` passing `chargeId` as `source_transaction` ONLY for card funding (:141-148 comment: ACH/SEPA settle via webhook ~4 days later). Tremendous rail skips programs without a campaign id (logged, not thrown). External rail fires `payout.confirmed` webhooks + batch emails with idempotency key `payout-confirmed-external/${invoiceId}`.
**Invariant:** (1) money-out rails that leave Dub's own balance (stablecoin/paypal/tremendous) must never run before the funding charge settles — otherwise Dub fronts reversible card money; connect transfers are safe because Stripe nets them against the charge via source_transaction or transfer debits; (2) the delayed retry re-enters at the TOP of the router, so method-backfill and gates re-run idempotently; (3) every rail is individually failure-isolated (allSettled) — one provider's outage cannot block the others.
**Probe:** deterministic probe: `grep -c 'allSettled' 'apps/web/app/(ee)/api/cron/payouts/charge-succeeded/route.ts'` = 1; `grep -n 'available_on \* 1000\|+ 15 \* 60 \* 1000' 'apps/web/app/(ee)/api/cron/payouts/charge-succeeded/utils.ts'` = :96,:107. No upstream unit suite (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getFundSettlementTiming", limit: 5 });
```

## Verdict
Adopt the settlement-gated rail router and the self-republishing delayed schedule (dedup + parallelism 1) as the canonical pattern for multi-rail money movement on a hosted queue. Adapt rails, buffers, and the Stripe balance-transaction probe. Omit the stablecoin financial-account pre-funding unless you run Stripe Financial Accounts.
