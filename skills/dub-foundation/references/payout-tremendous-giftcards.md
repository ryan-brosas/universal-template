<!-- capsule-v2 -->
# Tremendous gift-card payout — how do you deliver a combined reward with an idempotent external order, and why does non-EXECUTED status still mark payouts processed?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What are the amount-window gates and the status contract for the gift-card rail, including the counterintuitive failure path?

## sendTremendousPayouts: window gates → single folded order → EXECUTED-or-processed
**Path/Symbol:** `apps/web/lib/tremendous/send-tremendous-payouts.ts:sendTremendousPayouts` (:22-306); queue `apps/web/app/(ee)/api/cron/payouts/charge-succeeded/queue-tremendous-payouts.ts:queueTremendousPayouts` (:17-101); bounds + prohibited TLD list `apps/web/lib/tremendous/constants.ts:1-21`.
**Signature:** `sendTremendousPayouts({ partnerId, invoiceId?, forceWithdrawal? })`.
**Data Shape:** buckets = backlog (`status:"processed" ∧ tremendousOrderId:null ∧ mode:"internal" ∧ method:"tremendous" ∧ $5≤amount≤$2000`) + current invoice processing rows; order `{external_id:idempotencyKey, payment:{funding_source_id:"balance"}, reward:{campaign_id, value:{denomination:total/100,currency_code:"USD"}, recipient:{email}, delivery:{method:"LINK"}}}`.

### Decisive source
```ts
if (order.status !== "EXECUTED") {
  console.error(`Tremendous order ${order.id} status is not EXECUTED: ${order.status}`);
  await markPayoutsAsProcessed(currentInvoicePayouts);   // NOT failed — released for retry later
  return;
}
if (!redeemUrl) { ... await markPayoutsAsProcessed(currentInvoicePayouts); return; }
await prisma.payout.updateMany({ where: { id: { in: payoutIds } },
  data: { tremendousOrderId: order.id, status: "completed", paidAt: new Date(), method: "tremendous" } });
```
(:186-207)

**Flow:** partner must have tremendousEmail + payoutsEnabledAt (throw otherwise) → fold backlog+invoice buckets → total==0 skip; total outside [$500, $200_000] cents THROWS (hard config error) → deterministic key via createPayoutsIdempotencyKey → program must carry tremendousCampaignId (throw) → OrdersApi.createOrder (SDK client) → status/redeem-url ladder above → commissions→paid in 250-chunks → allSettled(activity log + per-payout referral queue jobs) → partner email with redeemUrl; queue side groups invoice partners by groupBy (amount-window + email present), skips campaign-less programs with a STRUCTURED log (`logger.error("missing_campaign")`) instead of throwing, then enqueues `${invoice.id}-${partnerId}` dedup'd jobs through a named QStash queue.
**Invariant:** (1) the redeem LINK is the money — if Tremendous accepted the order but no link came back, payouts go back to processed (not failed) so a later force-withdrawal re-attempts without double-spending (the external_id idempotency key makes the re-order safe); (2) only ONE order exists per partner-fold because every payout row is stamped with tremendousOrderId after success; (3) campaign-missing is a CONFIG condition: loud at queue time, fatal at execute time — never silently skipped at the moment money would move.
**Probe:** deterministic probe: `grep -n 'status !== "EXECUTED"' apps/web/lib/tremendous/send-tremendous-payouts.ts` = :186; `grep -c 'markPayoutsAsProcessed(currentInvoicePayouts)' apps/web/lib/tremendous/send-tremendous-payouts.ts` = 2. No upstream unit suite (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "sendTremendousPayouts", limit: 5 });
```

## Verdict
Adopt the fold-to-one-order pattern, the deterministic external_id, and the processed-not-failed degradation for provider-accepted-but-incomplete outcomes. Adapt SDK/campaign model and amount windows. Omit the prohibited-TLD/product-id tables unless you expose gift-card catalogs.
