<!-- capsule-v2 -->
# Payout processing invoice funnel — how do you flip eligible payouts onto an invoice, charge the program owner, and keep fee/usage math consistent across internal/hybrid/external modes?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What is the exact ordered contract when a program confirms payouts — from eligibility flip through Stripe charge — that a porter must not reorder?

## processPayouts: guarded updateMany claim → hybrid re-mode → groupBy totals → fee waiver → FX → idempotent PaymentIntent
**Path/Symbol:** `apps/web/app/(ee)/api/cron/payouts/process/process-payouts.ts:processPayouts` (:59-324); entry action `apps/web/lib/actions/partners/confirm-payouts.ts:confirmPayoutsAction` (:57-260); cutoff splitter `apps/web/app/(ee)/api/cron/payouts/process/split-payouts.ts:splitPayouts` (:12-110); constants `apps/web/lib/constants/payouts.ts`.
**Signature:** `processPayouts({ workspace, program, invoice, userId, paymentMethodId, cutoffPeriod?, selectedPayoutIds?, excludedPayoutIds? })`.
**Data Shape:** `payoutIdSelectionWhere` = `{id:{in:selected}}` XOR `{id:{notIn:excluded}}` else `{}` (`apps/web/lib/api/payouts/payout-id-selection-where.ts:4-18`); schema-level superRefine forbids combining both lists (confirm-payouts :43-49).

### Decisive source
```ts
const res = await prisma.payout.updateMany({
  where: { ...payoutIdSelectionWhere({ selectedPayoutIds, excludedPayoutIds }),
           ...getPayoutEligibilityFilter({ program }),          // pending + no invoice + min amount + mode gates
           ...(cutoffPeriodValue && { periodEnd: { lte: cutoffPeriodValue } }) },
  data: { invoiceId: invoice.id, status: "processing", userId, initiatedAt: new Date(),
          mode: program.payoutMode === "external" ? "external" : "internal" } });
if (res.count === 0) return;                                  // nothing claimed ⇒ skip everything
if (program.payoutMode === "hybrid") {
  await prisma.payout.updateMany({ where: { invoiceId: invoice.id,
    partner: { payoutsEnabledAt: null } }, data: { mode: "external" } }); }
```
(:73-119; charge tail)
```ts
await stripe.paymentIntents.create({ amount: totalToCharge, customer: workspace.stripeId!,
  payment_method_types: [paymentMethod.type], payment_method: paymentMethod.id,
  currency, confirmation_method: "automatic", confirm: true, transfer_group: invoice.id,
  ...(paymentMethod.type === "card"
      ? { statement_descriptor_suffix: "Dub Partners" }
      : { statement_descriptor: "Dub Partners" }) },
  { idempotencyKey: `process-payout-invoice/${invoice.id}` });
```
(:221-247)

**Flow:** confirm action validates (usage+amount ≤ limit; ≥ $10 min invoice; cutoff only when eligible count ≤ CUTOFF_PERIOD_MAX_PAYOUTS=1000 :32,:117-131; external payouts REQUIRE an active `payout.confirmed` webhook or the action throws `EXTERNAL_WEBHOOK_REQUIRED` :138-153; direct-debit mandate checked, invalid mandate detaches the payment method :176-193) → creates `inv_` invoice with count-based padded number inside a tx (:196-227) → QStash `process` with `deduplicationId: process-payouts-${invoice.id}` (:230-240) → cron claims payouts (above) → groupBy mode sums (:121-136) → `calculatePayoutFeeForMethod` adds 3% card hard cost to card/link (:8-25 of stripe/payment-methods.ts) → `calculatePayoutFeeWithWaiver` splits non-waivable rate vs waivable remainder, waiverLimit===0 ⇒ nothing free, fee = round(amount·hard) + round(charged·waivable) + fastACH flat (`apps/web/lib/partners/calculate-payout-fee-with-waiver.ts:16-53`) → SEPA/ACSS convert USD→local via Stripe fx_quotes with `(total/rate)·(1+FOREX_MARKUP_RATE)` and throw on rate ≤0 (:192-219) → PaymentIntent (idempotencyKey above) → increment workspace usage counters → enqueue `process/updates` side-effect walker.
**Invariant:** (1) the FIRST updateMany is the atomic claim — every later step keys off `invoiceId` rows it now owns; zero-count aborts before any money moves; (2) hybrid mode's external flip is a SECOND pass over just-claimed rows, never part of the first predicate (eligibility filter already required tenantId for those); (3) invoice numbers come from count+pad inside a transaction but uniqueness relies on the prefix convention — porters with concurrent invoicing need a real sequence; (4) the PaymentIntent is idempotent per invoice so QStash redelivery cannot double-charge.
**Probe:** deterministic probe: `grep -c 'updateMany' 'apps/web/app/(ee)/api/cron/payouts/process/process-payouts.ts'` = 2; `grep -n 'process-payout-invoice' 'apps/web/app/(ee)/api/cron/payouts/process/process-payouts.ts'` = :245. No upstream unit suite covers this route (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "processPayouts", limit: 5 });
```

## Verdict
Adopt the eligibility-filter claim + per-invoice idempotency key + waiver-aware fee composition as one unit; adopt the hybrid re-mode pass if you support mixed payout rails. Adapt Stripe specifics (descriptor rules, fx_quotes preview API), fee constants, and the cutoff-period catalog (CUTOFF_PERIOD values are computed at MODULE LOAD — serverless instances must rebuild them daily). Omit dub's program/workspace plan gating unless you have equivalent quotas. Coverage caveat: source-grounded, no upstream tests for this plane.
