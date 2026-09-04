<!-- capsule-v2 -->
# Payout lifecycle webhooks — how do Stripe payout.failed/payout.paid and balance.available map onto dub's payout rows, and which transitions are keyed by provider ids?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** After a Connect transfer lands in a partner's bank, what closes the loop — and what does the balance.available auto-withdrawal do differently?

## payout-failed / payout-paid / balance-available routes
**Path/Symbol:** `apps/web/app/(ee)/api/cron/payouts/payout-failed/route.ts:POST` (:20-84); `.../payout-paid/route.ts:POST` (:21-88); `.../balance-available/route.ts:POST` (:24-220); account-status table `apps/web/lib/constants/payouts.ts:BANK_ACCOUNT_STATUS_DESCRIPTIONS` (:49-77).
**Signature:** QStash-verified POSTs `{stripeAccount, stripePayout:{id,...}}`; row lookup is by `stripePayoutId` (failed/paid) or transfer-id reconciliation (balance-available).
**Data Shape:** payout-paid carries `traceId` → persisted as `stripePayoutTraceId` (surfaced to APIs as `traceId`); HUF/TWD balances are floored to whole hundreds (Stripe divisibility rule :133-136).

### Decisive source
```ts
const updatedPayouts = await prisma.payout.updateMany({
  where: { stripePayoutId: stripePayout.id },
  data: { status: "failed", failureReason: stripePayout.failureMessage } });
```
(payout-failed :46-55)
```ts
data: { status: "completed", stripePayoutTraceId: stripePayout.traceId }
```
(payout-paid :50-53)
```ts
where: { partnerId: partner.id, OR: [
  { status: "sent", stripePayoutId: null,
    stripeTransferId: { in: transfers.data.map(({id}) => id) } },   // transfers now cashing out
  { status: "failed", stripePayoutId: { not: null } } ] },          // previously failed ⇒ re-tag
data: { stripePayoutId: stripePayout.id }
```
(balance-available :167-186)

**Flow:** payout-failed/payout-paid resolve the PARTNER by connect account id, bulk-update every payout row stamped with that provider payout id, then email (failed ⇒ action-required with bank status; paid ⇒ completed with trace). balance-available is the AUTO-WITHDRAWAL engine for partners who leave money in their Connect account: retrieve balance → zero-available-but-pending ⇒ self-republish in 1 hour → invalid bank-account status ⇒ action-required email and stop → create a standard Stripe payout on the CONNECT account (`stripe.payouts.create` with `stripeAccount`) → list the account's incoming transfers and attach the new payout id onto all sent-unpaid rows funded by those transfers PLUS any previously failed rows → initiated email with `Idempotency-Key: payout-initiated-${stripePayout.id}`.
**Invariant:** (1) provider payout ids — not dub ids — key the terminal transitions, so one Stripe payout covering N dub payouts updates them in one updateMany; (2) failure is recoverable state: failed rows with a stripePayoutId get RE-TAGGED by the next auto-withdrawal instead of being orphaned; (3) the pending-balance retry loop lives entirely in QStash delays, never in a long-running poller.
**Probe:** deterministic probe: `grep -c 'stripePayoutId: stripePayout.id' 'apps/web/app/(ee)/api/cron/payouts/balance-available/route.ts' 'apps/web/app/(ee)/api/cron/payouts/payout-failed/route.ts' | paste -sd' '` shows 3 total sites; `grep -n 'Math.floor(availableBalance / 100) \* 100' 'apps/web/app/(ee)/api/cron/payouts/balance-available/route.ts'` = :135. No upstream unit suite (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "stripeAccount", limit: 8 });
```

## Verdict
Adopt provider-id-keyed terminal transitions plus the re-tag-on-retry recovery rule. Adapt currency-divisibility quirks and email templates. Omit the HUF/TWD special case when your currencies don't need it.
