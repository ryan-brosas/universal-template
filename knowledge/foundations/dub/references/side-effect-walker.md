<!-- capsule-v2 -->
# Recursive side-effect walker — how do you run audit logs + emails for thousands of invoice payouts without exceeding a serverless invocation, and why cursor+skip:1?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What is the self-reinvoking pagination contract for post-charge side effects, and which side effect is conditional on payment method?

## process/updates route: take BATCH_SIZE → skip:1+cursor → requeue on full page
**Path/Symbol:** `apps/web/app/(ee)/api/cron/payouts/process/updates/route.ts:POST` (:22-140); force-withdrawal walker `apps/web/app/(ee)/api/cron/payouts/force-withdrawals/route.ts:GET` (:22-100+, BATCH_SIZE=20, 90-day idle partners); payout export generator `apps/web/app/(ee)/api/cron/export/payouts/fetch-payouts-batch.ts:fetchPayoutsBatch` (:10-40).
**Signature:** payload `{invoiceId, startingAfter?}`; query `take:BATCH_SIZE, skip: startingAfter?1:0, cursor:{id}, orderBy id asc`; BATCH_SIZE=100.
**Data Shape:** full page (length===BATCH_SIZE) ⇒ requeue with `startingAfter = last.id`; short page ⇒ terminal log. Audit actor falls back to `"system"` when `payout.userId` is null.

### Decisive source
```ts
if (payouts.length === BATCH_SIZE) {
  const nextStartingAfter = payouts[payouts.length - 1].id;
  await qstash.publishJSON({ url: `.../api/cron/payouts/process/updates`,
    body: { invoiceId, startingAfter: nextStartingAfter } });
  return logAndRespond(`Enqueued next batch ...`);
}
```
(:117-131)
```ts
if (invoice && invoice.paymentMethod !== "card" &&
    internalPayouts.length > 0) { await sendBatchEmail(...); }   // card ⇒ no early email
```
(:92-115)

**Flow:** each invocation audits its 100 payouts (`payout.confirmed`, per-payout target metadata) → batch-emails "payout is on the way" to INTERNAL-mode payouts only when the invoice was NOT paid by card (card charges settle instantly so the later "processed" email suffices; direct debits take days) → full page ⇒ QStash-reinvoke at the cursor; done ⇒ log. The same walker pattern drives daily 90-day force-withdrawals (partner scan + per-partner allSettled + self-requeue) and the async payout CSV exporter, where an async-generator yields pages until `hasMore = payouts.length === pageSize` and a 100k-row cap trims the final slice.
**Invariant:** (1) `skip:1 + cursor` is Prisma's keyset form — the cursor row itself is excluded so no row is processed twice across invocations; offset paging would duplicate or drop rows as writes land mid-walk; (2) termination is guaranteed by the strict full-page test — a page of exactly BATCH_SIZE followed by nothing costs one extra empty invocation but never loops forever; (3) side effects are batched per invocation so one slow email provider delays only its own 100 rows.
**Probe:** deterministic probe: `grep -n 'skip: startingAfter ? 1 : 0' 'apps/web/app/(ee)/api/cron/payouts/process/updates/route.ts'` = :47; `grep -c 'paymentMethod !== "card"' 'apps/web/app/(ee)/api/cron/payouts/process/updates/route.ts'` = 1. No upstream unit suite (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "recordAuditLog", limit: 5 });
```

## Verdict
Adopt the cursor+skip:1 self-requeue walker for any bounded-memory fan-out over queue delivery. Adapt batch sizes and the card-vs-debit email policy to your rails. Omit the R2-signed-export variant unless you need large CSV downloads.
