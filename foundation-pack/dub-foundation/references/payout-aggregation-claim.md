<!-- capsule-v2 -->
# Commission aggregation claim — how do you aggregate due commissions into payouts without two workers claiming the same commission (and why raw SQL instead of Prisma updateMany)?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What makes the per-commission claim race-proof when a cron aggregates pending commissions into payouts, and why does it bypass Prisma's updateMany?

## aggregateDueCommissionsForPartner: create-empty-payout → raw-SQL guarded claim → DB-truth amount
**Path/Symbol:** `apps/web/app/(ee)/api/cron/payouts/aggregate-due-commissions/process/route.ts:aggregateDueCommissionsForPartner` (:219-362); driver POST :28-217; `MUTABLE_PAYOUT_STATUSES = ["pending","canceled"]` at `apps/web/lib/constants/payouts.ts:47`.
**Signature:** `aggregateDueCommissionsForPartner({ partnerId, program, commissions, existingPendingPayout? }): Promise<boolean>`; BATCH_SIZE=100 fetch loop; partners chunked 50-wide under `Promise.allSettled` (:150-196).
**Data Shape:** input commissions are `pending` only, sorted by createdAt asc; periodStart/periodEnd derive from first/last claimed; payout created with `amount: 0` and filled from an aggregate AFTER the claim — never from a precomputed client-side sum.

### Decisive source
```ts
// Use raw SQL instead of prisma.commission.updateMany.
// Prisma has a reported MySQL issue where updateMany may drop WHERE predicates
// during the UPDATE, allowing concurrent workers to claim the same commissions.
// See: https://github.com/prisma/prisma/issues/28840
// Also join Payout so we never attach to a payout that left a mutable status
const updatedCommissions = await prisma.$executeRaw`
  UPDATE Commission c
  INNER JOIN Payout p ON p.id = ${payoutToUse.id}
  SET c.status = ${CommissionStatus.processed}, c.payoutId = ${payoutToUse.id}, c.updatedAt = NOW()
  WHERE c.id IN (${Prisma.join(commissionIds)})
    AND c.programId = ${program.id} AND c.partnerId = ${partnerId}
    AND c.status = ${CommissionStatus.pending}
    AND p.status IN (${Prisma.join(MUTABLE_PAYOUT_STATUSES)})`;
if (updatedCommissions === 0) {
  if (!isReusingPendingPayout) await prisma.payout.deleteMany({
    where: { id: payoutToUse.id, commissions: { none: {} } } });   // delete ONLY if still empty
  return false;
}
// Always set amount from DB after claim (create + reuse) so partial claims
// and concurrent attaches cannot leave a stale precomputed sum.
```
(:266-318; second raw UPDATE re-guards the payout itself :320-335: `UPDATE Payout SET amount=…, periodEnd=COALESCE(${isReusingPendingPayout ? periodEnd : null}, periodEnd) WHERE id=… AND status IN (MUTABLE)`)

**Flow:** groupBy partnerGroups by holdingPeriodDays → per holding-period `while(true)`: fetch 100 oldest pending commissions (`OR[type IN custom,referral] ∨ createdAt < now−holdingPeriodDays` when holding >0 — custom/referral always included :89-107) → bucket by partner → for each 50-partner chunk prefetch existing pending payouts into a Map → reuse-or-create payout → guarded claim UPDATE → zero rows ⇒ cleanup empty new payout + return false → aggregate SUM(earnings) as DB truth → second guarded payout UPDATE → activity-log only commissions verified claimed (`payoutId=payout ∧ status=processed`, :338-352). Driver breaks a holding-period loop when totalProcessed===0 so persistent failure cannot spin forever (:205-210).
**Invariant:** (1) claim atomicity comes from the WHERE predicates surviving to SQL — porting this back to Prisma `updateMany` on MySQL reintroduces the lost-predicate race (issue #28840); (2) a payout is attachable only while its status ∈ {pending, canceled} — enforced via JOIN at claim time AND again on the amount write, closing the confirm-between-prefetch-and-claim window; (3) amounts are recomputed post-claim, never trusted across awaits; (4) failed claims never delete a reused payout (it may hold other commissions).
**Probe:** deterministic probe: `grep -c 'prisma.\$executeRaw' 'apps/web/app/(ee)/api/cron/payouts/aggregate-due-commissions/process/route.ts'` = 2; `grep -c 'MUTABLE_PAYOUT_STATUSES' apps/web/lib/api/commissions/reconcile-payout-amounts.ts` = 3. No upstream unit suite exists for this route (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "aggregateDueCommissionsForPartner", limit: 5 });
```

## Verdict
Adopt the create-empty→guarded-claim→recompute-from-DB ladder and the mutable-status join guard verbatim for any ledger aggregation with concurrent consumers; adopt the "custom/referral bypass holding period" business rule only if your program semantics match. Adapt statuses, table names, and the holding-period windows. Omit dub's partner-group/holding-period domain model unless you have equivalent cohort rules. Coverage caveat: no direct unit tests exist upstream for this cron route; behavior is source-grounded.
