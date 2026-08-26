<!-- capsule-v2 -->
# Cutoff-period payout splitting — how do you pay only pre-cutoff commissions while keeping the rest pending, and what is the 1000-payout guard?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** How does a chosen cutoff period reshape existing payouts before processing, and which rows move to the new month?

## splitPayouts: per-payout commission partition → amend old + create current-month payout
**Path/Symbol:** `apps/web/app/(ee)/api/cron/payouts/process/split-payouts.ts:splitPayouts` (:12-110); cutoff catalog `apps/web/lib/partners/cutoff-period.ts:CUTOFF_PERIOD` (:9-35); guard constant `apps/web/lib/constants/payouts.ts:CUTOFF_PERIOD_MAX_PAYOUTS=1000` (:33).
**Signature:** `splitPayouts({program, cutoffPeriod, selectedPayoutIds?, excludedPayoutIds?})`; eligibility via the SAME getPayoutEligibilityFilter + selection where as the claim.
**Data Shape:** cutoff values are computed at MODULE LOAD (`endOfMonth(subMonths(now,1))` etc.); "today" transforms to undefined in the zod enum (no-op). Payouts carry commissions include; periodEnd rewritten with `endOfMonth(lastPreCutoffCommission.createdAt)`.

### Decisive source
```ts
if (previousCommissionsCount > 0) {
  await prisma.payout.update({ where: { id: payout.id },
    data: { periodEnd: endOfMonth(previousCommissions[pc.length-1].createdAt),
            amount: previousCommissions.reduce((t,c)=>t+c.earnings,0) } });
  if (currentCommissionsCount > 0) {
    const currentMonthPayout = await prisma.payout.create({ data: { id: createId({prefix:"po_"}),
      ..., periodStart: cc[0].createdAt, periodEnd: cc[cc.length-1].createdAt,
      amount: cc.reduce((t,c)=>t+c.earnings,0) } });
    await prisma.commission.updateMany({ where: { id: { in: currentCommissions.map(c=>c.id) } },
      data: { payoutId: currentMonthPayout.id } }); } }
```
(:64-107)

**Flow:** fetch all eligible payouts WITH commissions → per payout partition commissions at the cutoff instant → pre-cutoff exist ⇒ rewrite the ORIGINAL payout's envelope+amount to just those; post-cutoff exist ⇒ mint a NEW `po_` payout for them and re-point their commission rows → payouts entirely on one side are untouched. The confirm action refuses cutoff periods when eligible count > 1000 (TODO in source: pre-cutoff splitting not supported at that scale) — callers must process without a cutoff instead.
**Invariant:** (1) commission membership is moved, never duplicated — amounts on both sides derive from their OWN commission lists so SUM(commission.earnings) stays equal to payout.amount after the split; (2) the original payout keeps its id (external references stable) and only its envelope changes; (3) module-load dates mean a long-lived server caches stale cutoff boundaries — serverless-per-request evaluation or daily rebuild required.
**Probe:** deterministic probe: `grep -n 'payoutId: currentMonthPayout.id' 'apps/web/app/(ee)/api/cron/payouts/process/split-payouts.ts'` = :104; `grep -n 'CUTOFF_PERIOD_MAX_PAYOUTS = 1000' apps/web/lib/constants/payouts.ts` = :33. No upstream unit suite covers this file (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "splitPayouts", limit: 5 });
```

## Verdict
Adopt the partition-and-repoint split preserving the original row id, plus the scale guard that degrades to no-cutoff processing. Adapt the period catalog to your billing calendar. Omit the endOfMonth rounding if your cutoffs are exact timestamps.
