<!-- capsule-v2 -->
# Batched row transfer ladder — how do you re-point millions of FK rows to a new owner without a timeout, and fold the duplicates it creates?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1` (drift pass). **Question:** What is the correct batching primitive for high-volume ownership-transfer `updateMany` calls, and how do you reconcile duplicate child rows afterwards?

## transferRowsInBatches + combinePendingPayouts
**Path/Symbol:** `apps/web/app/(ee)/api/workflows/merge-partner-accounts/route.ts:transferRowsInBatches` (:351-368) and `combinePendingPayouts` (:708-795).
**Signature:** `transferRowsInBatches(updateBatch: () => Promise<number>, { resourceName }): Promise<void>`; `combinePendingPayouts({ partnerId, programId })`.
**Data Shape:** `updateBatch` closes over an `updateMany({...payload, limit: PRISMA_UPDATEMANY_LIMIT})`; the count return drives loop termination. Payouts: pending-only, oldest-first, period bounds nullable.

### Decisive source
```ts
async function transferRowsInBatches(updateBatch, { resourceName }) {
  while (true) {
    const count = await updateBatch();
    console.log(`Transferred ${count} ${resourceName} in batch`);
    if (count < PRISMA_UPDATEMANY_LIMIT) break;   // short batch = drained
  }
}
// after payouts are moved onto the target partner:
await prisma.payout.update({ where: { id: combinedPayoutId },
  data: { amount: totalAmount, periodStart, periodEnd } });
await transferRowsInBatches(async () =>
  (await prisma.commission.updateMany({
    where: { payoutId: { in: payoutIdsToDelete } },
    data: { payoutId: combinedPayoutId }, limit: PRISMA_UPDATEMANY_LIMIT,
  })).count, { resourceName: "commission" });
await prisma.payout.deleteMany({ where: { id: { in: payoutIdsToDelete } } });
```

**Flow:** loop updateMany-with-limit until a batch returns fewer rows than the limit → for payouts, folding happens AFTER the move created duplicates: keep the OLDEST payout as survivor (`payoutsToCombine[0].id`), sum amounts, widen periodStart/periodEnd to min/max across all pending payouts, re-point every commission from doomed payout ids to the survivor in batches, then delete the losers.
**Invariant:** termination is count-driven — `count < LIMIT` is the ONLY exit; the same WHERE must be replayable because each batch re-matches only remaining source rows (the predicate advances as rows flip). Folding order matters: update survivor amount/period FIRST, then re-point children, then delete donors — reversing it orphans commissions on deleted payouts. Low-volume tables skip batching entirely (single updateMany) — don't pay the loop where volume doesn't demand it.
**Probe:** no direct unit test pins this helper upstream (it runs inside the merge workflow covered by `tests/workflows/merge-partner-accounts-workflow.test.ts` end-to-end); coverage caveat — deterministic probe: after a merge with >LIMIT commissions, zero rows remain with `partnerId = sourcePartnerId`, and exactly one pending payout survives per (partnerId, programId).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "transferRowsInBatches combinePendingPayouts", limit: 6 });
// → route.ts transferRowsInBatches 351-368, combinePendingPayouts 708-795
```

## Verdict
Adopt the count-driven limited-updateMany loop for any bulk ownership change and oldest-survivor fold semantics for duplicated aggregates. Adapt PRISMA_UPDATEMANY_LIMIT to your driver's practical ceiling. Omit payout folding without a payouts ledger.
