<!-- capsule-v2 -->
# Commission hold & side-effect gating — how does fraud risk hold a payout without losing its side effects?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** After a commission row exists, when does it get flipped to hold, and which downstream effects run for held/clawback commissions?

## stepRunSideEffects: two-source hold decision → pending-guarded flip → allSettled fan-out with per-effect predicates
**Path/Symbol:** `apps/web/app/(ee)/api/workflows/create-partner-commission/route.ts:stepRunSideEffects` (:487-724).
**Signature:** `stepRunSideEffects(input: StepFunctionInput & { commission: Pick<Commission,"id"> | null }): Promise<Array<{ step: string; result: PromiseSettledResult }>>`.
**Data Shape:** `PARTNER_LEVEL_FRAUD_RULES` (partner-scope rule types); commission statuses pending/processed/paid/hold/fraud/canceled; clawback = negative earnings.

### Decisive source
```ts
// 1. Partner-level: any pending partner-scope fraud group -> hold.
// 2. Conversion-event: run fraud detection before create; if rules trigger -> hold.
let shouldHoldCommission =
  riskRulesTriggered ||
  (await prisma.fraudEventGroup.findFirst({ where: { programId, partnerId,
      status: FraudEventStatus.pending, type: { in: PARTNER_LEVEL_FRAUD_RULES } } })) !== null;

// An explicit `status` input (e.g. imports) wins; clawbacks are never held.
if (shouldHoldCommission && !status && commission.earnings > 0
    && commission.status === CommissionStatus.pending) {
  try {
    commission = await prisma.commission.update({
      where: { id: commission.id, status: CommissionStatus.pending },   // guarded
      data: { status: CommissionStatus.hold }, include: commissionInclude });
    await trackCommissionStatusUpdate({ ..., newStatus: CommissionStatus.hold });
  } catch (error) {
    // re-fetch so side effects use the current status from the database.
    commission = await prisma.commission.findUniqueOrThrow({ ... });
  }
}
const shouldTriggerWorkflow = !isClawback && !skipWorkflow && !isOnHold;
```
(:581-611 hold sources + guards, condensed; :638-648 refetch; :652-653 trigger gate)

**Flow:** optional risk monitoring (`detectAndRecordFraudEvent`) only when customer+eventId+clickEvent present · hold decision from EITHER just-triggered rules OR an existing pending partner-level group · flip is WHERE-guarded to pending (concurrent status change ⇒ catch → re-fetch, never crash) · fan-out via `Promise.allSettled`: webhook always; postback always; `syncTotalCommissions` skipped when on-hold (held earnings must not inflate totals); partner notification skipped for clawback AND hold; workflow execution gated by `!isClawback && !skipWorkflow && !isOnHold`; optional aggregate-due trigger · results returned as named `{step, result}` rows.
**Invariant:** (1) hold is a STATUS TRANSITION with a guard, not a blind write — a commission already processed/paid by a race keeps its state and the code adapts from the re-fetched truth; (2) held commissions still emit webhooks/postbacks (consumers must see the hold) but skip sync/notify/workflows — the asymmetry is the point; (3) explicit input status (imports) outranks automatic holding; (4) one failed side effect never aborts siblings — failures surface in the returned result rows for the caller to log.
**Probe:** deterministic probe: `grep -c 'isOnHold' apps/web/app/\(ee\)/api/workflows/create-partner-commission/route.ts` = 3 and `grep -c 'shouldTriggerWorkflow\|isClawback' ...route.ts` = 4; suites in `tests/fraud/` and `tests/commissions/`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "stepRunSideEffects", limit: 5 });
// → dub.apps.web.app.(ee).api.workflows.create-partner-commission.route.stepRunSideEffects @ route.ts 487-724
```

## Verdict
Adopt the dual-source hold decision, pending-guarded flip with refetch fallback, and per-effect predicate fan-out. Adapt your fraud-rule taxonomy. Omit dub's plan-capability gate if you have no plan tiers.
