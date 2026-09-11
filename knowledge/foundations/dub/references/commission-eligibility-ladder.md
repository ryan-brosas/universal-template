<!-- capsule-v2 -->
# Commission eligibility ladder — which skip gates decide lead/sale commission creation, in what order?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What is the ordered gate sequence between "event received" and "commission row written" that a porter must reproduce exactly?

## stepCreateCommission: event gates → first-commission context → reward resolution → duration/spend caps → P2002-aware write
**Path/Symbol:** `apps/web/app/(ee)/api/workflows/create-partner-commission/route.ts:stepCreateCommission` (:177-485).
**Signature:** `stepCreateCommission(input: Input & { programEnrollment }): Promise<{ commission: Pick<Commission,"id"> | null; outputLog: string; isFirstCommission?: boolean }>`.
**Data Shape:** events `lead|sale|custom` here (click/referral refused); `firstCommission = earliest (partnerId, customerId, type=event)` row's `{rewardId,status,createdAt}`; rewards carry `maxDuration`, `spendLimitAmount/Interval`.

### Decisive source
```ts
if (firstCommission) {
  if (["fraud", "canceled"].includes(firstCommission.status)) return skip;
  if (event === "lead") return skip;   // one lead reward per customer, ever
  // sale: original one-time reward (maxDuration === 0) still blocks recurrence
  if (firstCommission.rewardId && firstCommission.rewardId !== reward.id) {
    const originalReward = await prisma.reward.findUnique({ where: { id: firstCommission.rewardId } });
    if (originalReward?.maxDuration === 0) return skip;
  }
}
if (typeof reward?.maxDuration === "number") {
  if (reward.maxDuration === 0) return skip;                    // one-time
  const subscriptionDurationMonths = differenceInMonths(createdAt ?? new Date(), firstCommission.createdAt);
  if (subscriptionDurationMonths >= reward.maxDuration) return skip;
} else {
  earnings = rewards.reduce((acc, { reward, sale }) => acc + calculateSaleEarnings({ reward, sale }), 0);
}
```
(:300-371 condensed; zero-earnings gate :392-397)

**Flow:** amount coercion → click/refusal + enrollment-eligibility gates → `custom` takes raw amount · otherwise fetch firstCommission and DERIVE subscription context (`subscriptionStartDate = firstCommission?.createdAt ?? new Date()` for sales, `type: firstCommission ? "recurring" : "new"`) BEFORE `determinePartnerRewards` so condition-gated rewards see it → no-reward skip → the ladder above → zero-earnings skip → spend-limit clamp via `clampEarningsToSpendLimit` (:729-791: window aggregate over pending/processed/paid/hold incl. customer scope for sales; `Math.max(0, min(earnings, limit - used))`, clamped-to-zero skips with a human description) → create with `eventId || null` normalization → catch: non-P2002 errors Slack-alert AND `throw new WorkflowRetryAfterError(msg, "5s")`; P2002 (unique violation = duplicate event) returns null-commission quietly.
**Invariant:** (1) gate ORDER is the contract — fraud/canceled beats lead-once beats max-duration beats spend-limit, so a fraud-flagged customer relationship can never be monetized by re-configuring rewards; (2) recurring detection depends on the FIRST commission's ORIGINAL reward surviving deletion of newer configs; (3) duplicate delivery is answered by the DB unique constraint, not by idempotency keys — P2002 IS the dedup success path.
**Probe:** deterministic probe: `grep -c 'return logAndReturn({' apps/web/app/\(ee\)/api/workflows/create-partner-commission/route.ts` = 15 (every gate returns the same tuple shape); suites in `tests/commissions/`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "stepCreateCommission", limit: 5 });
// → dub.apps.web.app.(ee).api.workflows.create-partner-commission.route.stepCreateCommission @ route.ts 177-485
```

## Verdict
Adopt the ordered eligibility ladder, first-commission-derived subscription context, and P2002-as-dedup write posture. Adapt reward vocabulary. Omit dub's currency formatting.
