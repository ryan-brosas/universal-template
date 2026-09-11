<!-- capsule-v2 -->
# Commission hold plane — plan-gated bulk hold of pending and processed commissions with re-verification after every updateMany

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** When a partner-level fraud group lands, which commissions may be frozen, why must the code re-fetch after updateMany, and what happens to commissions already sitting in a PENDING payout?

## Two whole-file ladders sharing the chunk(50) × while(true) × LIMIT=250 skeleton
**Path/Symbol:** `apps/web/lib/api/fraud/hold-pending-commissions.ts:holdPendingCommissions` (:10-149) + `hold-processed-commissions.ts:holdProcessedCommissions` (:165-319).
**Signature:** both `async function holdXCommissions(programEnrollments: Pick<ProgramEnrollment,"programId"|"partnerId">[])`; eligibility where = `{ status, earnings: { gt: 0 }, program: { workspace: { plan: { in: ["enterprise","advanced"] } } } }`.
**Data Shape:** pending variant holds `CommissionStatus.pending`; processed variant holds `processed` rows whose `payout.status === PayoutStatus.pending`, ALSO setting `payoutId: null`, and retallies touched payouts at the end.

### Decisive source
```ts
const chunks = chunk(uniquePairs, 50);
for (const chunk of chunks) { while (true) {
  const found = await prisma.commission.findMany({ where: { OR: pairs, ...holdEligibleWhere }, take: PRISMA_UPDATEMANY_LIMIT });
  if (found.length === 0) break;
  const { count: updatedCount } = await prisma.commission.updateMany({
    where: { id: { in: found.map((c) => c.id) }, ...holdEligibleWhere },   // RE-CHECKS eligibility
    data: { status: "hold" /* + payoutId: null in processed variant */ } });
  if (updatedCount === 0) break;
  if (updatedCount < found.length) {          // some rows raced: refetch ONLY actually-held
    const heldIds = new Set((await prisma.commission.findMany({
      where: { id: { in: ids }, status: "hold" }, select: { id: true } })).map((c) => c.id));
    heldCommissions = found.filter((c) => heldIds.has(c.id)); }
  ... trackCommissionStatusUpdate per program; syncTotalCommissions per affected pair ...
} }
await retallyPayoutsAmount(Array.from(payoutIdsToRetallySet));  // processed variant only
```
(hold-pending-commissions.ts :40-147 / hold-processed-commissions.ts :200-318 condensed; PRISMA_UPDATEMANY_LIMIT=250 at lib/cron/index.ts:25)

**Flow:** dedupe enrollment pairs → chunk 50 → find-take-250 → guarded updateMany → drift reconciliation (refetch-actually-held when count < fetched) → activity logs grouped BY PROGRAM (workspace-scoped logs) → partner totals sync (Promise.all in pending / allSettled in processed) → processed variant detaches payout links and retallies those payouts so their amounts shrink correctly.
**Invariant:** (1) the updateMany where REPEATS the full eligibility predicate — a commission aggregated into a payout between find and update silently escapes this batch (comment :92-93 documents it); logging/sync only touch rows CONFIRMED held via the refetch; (2) plan gate lives INSIDE the query — free-plan workspaces never match regardless of caller; (3) earnings > 0 excludes clawbacks from holds; (4) processed-hold requires the payout to still be `pending` — once invoiced/processing, money movement is rail-owned and untouchable by fraud holds; (5) `payoutId: null` detach + later `retallyPayoutsAmount` keeps payout amounts truthful without rewriting invoice-bound rows.
**Probe:** anchored at dub repo root: `grep -o 'PRISMA_UPDATEMANY_LIMIT' apps/web/lib/api/fraud/hold-pending-commissions.ts | wc -l` = **2**; `grep -cF '["enterprise", "advanced"]' apps/web/lib/api/fraud/hold-pending-commissions.ts` = **1**; `grep -c 'chunk(uniquePairs, 50)' apps/web/lib/api/fraud/hold-pending-commissions.ts` = **1**; `grep -c 'payoutId: null' apps/web/lib/api/fraud/hold-processed-commissions.ts` = **1**; `grep -o 'retallyPayoutsAmount' apps/web/lib/api/fraud/hold-processed-commissions.ts | wc -l` = **2**; `grep -c 'PRISMA_UPDATEMANY_LIMIT = 250' apps/web/lib/cron/index.ts` = **1**. Direct tests: none isolated (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "holdProcessedCommissions", limit: 5 });
```

## Verdict
Adopt the re-verify-after-updateMany discipline and the payout-status boundary on processed holds. Adapt plan gating to your billing model. Omit the console noise; keep the per-program log grouping.
