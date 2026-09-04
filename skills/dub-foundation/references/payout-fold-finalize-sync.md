<!-- capsule-v2 -->
# Payout fold & finalize sync — how do you collapse duplicate pending payouts and make post-transfer reconciliation retry-safe?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What is the fold order when two partners' payouts merge, and why must the finalize step throw on partial sync failure?

## combinePendingPayouts + syncLinksAndCommissions: oldest-survivor fold, allSettled-then-throw
**Path/Symbol:** `apps/web/app/(ee)/api/workflows/merge-partner-accounts/route.ts:combinePendingPayouts` (:708-794) and `syncLinksAndCommissions` (:796-844); finalize step :98-118.
**Signature:** `combinePendingPayouts({ partnerId, programId })`; `syncLinksAndCommissions({ targetPartnerId, programIdsToTransfer })`.
**Data Shape:** payout fields `status`, `periodStart/periodEnd` (nullable), `amount`; commission carries nullable `payoutId`.

### Decisive source
```ts
const combinedPayoutId = payoutsToCombine[0].id;          // OLDEST survives (orderBy createdAt asc)
const payoutIdsToDelete = payoutsToCombine.slice(1).map((p) => p.id);
await prisma.payout.update({ where: { id: combinedPayoutId },
  data: { amount: totalAmount, periodStart, periodEnd } });  // widened envelope
await transferRowsInBatches(async () =>
  (await prisma.commission.updateMany({
    where: { payoutId: { in: payoutIdsToDelete } },
    data: { payoutId: combinedPayoutId }, limit: PRISMA_UPDATEMANY_LIMIT,
  })).count, { resourceName: "commission" });
await prisma.payout.deleteMany({ where: { id: { in: payoutIdsToDelete } } });
```
(:751-789 survivor fold)
```ts
const rejected = res.filter((r): r is PromiseRejectedResult => r.status === "rejected");
if (rejected.length > 0) {
  throw new Error(`Failed to sync links/commissions: ...`);   // fail the STEP
}
// Fail the step (so QStash retries it) if any sync rejected. All of these
// ops are idempotent, so re-running the step is safe.
```
(:827-839 allSettled-then-throw)

**Flow:** fold runs per-program after every data move: pending payouts sorted oldest-first → survivor keeps the earliest id but WIDENS its period to min(start)/max(end) across all folded payouts and sums amounts → children commissions re-pointed in batches → donors deleted. Finalize step then re-fetches the target's transferred links (with tags + enrollment includes) and runs `recordLink` (Tinybird), `linkCache.expireMany`, and per-program `syncTotalCommissions` under `Promise.allSettled`.
**Invariant:** (1) survivor = oldest so payout ids referenced by external statements stay stable; (2) commissions move BEFORE donor deletion — deleting first would orphan their payoutId references; (3) the finalize step COLLECTS all sync results before deciding: throwing on ANY rejection converts partial warehouse/cache drift into a queue retry of an idempotent step, while swallowing would leave Tinybird/DB silently divergent — never allSettled-and-forget here; (4) period nulls degrade to `payoutsToCombine[0]` values rather than fabricating dates.
**Probe:** deterministic probe: `grep -c 'payoutIdsToDelete' apps/web/app/\(ee\)/api/workflows/merge-partner-accounts/route.ts` = 3; `grep -n 'rejected.length > 0' ...route.ts` = :833.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "combinePendingPayouts", limit: 5 });
// → ...route.combinePendingPayouts @ route.ts 708-794
```

## Verdict
Adopt oldest-survivor folding with envelope-widening and children-before-donor deletion, plus collect-then-throw reconciliation for idempotent finalizers. Adapt amounts/period semantics. Omit dub's payout hold periods.
