<!-- capsule-v2 -->
# Payout status counts & eligibility badge — why does the count API offer an "eligibility" switch, and how do tabs stay stable across empty statuses?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** How does /api/payouts/count serve both raw filtering and payability previewing from one handler?

## payouts/count dual-mode where
**Path/Symbol:** `apps/web/app/(ee)/api/payouts/count/route.ts:GET` (:71-144); eligibility predicate `apps/web/lib/api/payouts/payout-eligibility-filter.ts`.
**Signature:** `GET {status?, partnerId?, groupId?, groupBy?: "status", eligibility?: "eligible", invoiceId?}`.
**Data Shape:** `eligibility:"eligible"` SPREADS getPayoutEligibilityFilter into the where (replacing the default status filter path) — the response then reports what a confirm action would claim RIGHT NOW; programEnrollment filter supports NOT-IN group exclusion via parseFilterValue.

### Decisive source
```ts
const where: Prisma.PayoutWhereInput = {
  programId,
  ...(partnerId && { partnerId }),
  ...(eligibility === "eligible" && { ...getPayoutEligibilityFilter({ program }) }),
  ...(invoiceId && { invoiceId }),
  ...(programEnrollment && { programEnrollment }) };
if (groupBy === "status") {
  const payouts = await prisma.payout.groupBy({ by: ["status"], where, _count: true, _sum: { amount: true } });
  const counts = payouts.map((p) => ({ status: p.status, count: p._count, amount: p._sum.amount }));
  Object.values(PayoutStatus).forEach((status) => {
    if (!counts.find((p) => p.status === status)) counts.push({ status, count: 0, amount: 0 }); });
```
(:86-123)

**Flow:** one where-object assembled conditionally → branch on groupBy: per-status buckets (zero-filled against the full enum) or single aggregate row. The zero-fill keeps dashboard tab order/labels static regardless of data.
**Invariant:** (1) the eligible-badge numbers come from the SAME filter the claim uses — no second source of truth to drift; (2) zero-filling happens SERVER-side so clients never special-case missing statuses; (3) amount sums ride alongside counts (tabs show money, not just rows).
**Probe:** deterministic probe: `grep -n 'eligibility === "eligible"' 'apps/web/app/(ee)/api/payouts/count/route.ts'` = :89; `grep -c 'counts.push' 'apps/web/app/(ee)/api/payouts/count/route.ts'` = 1. No upstream unit suite covers this route directly (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getPayoutsCount", limit: 5 });
```

## Verdict
Adopt shared-predicate badges + server-side enum zero-fill. Adapt statuses. Omit the enrollment NOT-IN path if you have no groups feature.
