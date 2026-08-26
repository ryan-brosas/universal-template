<!-- capsule-v2 -->
# Conversion-time hold integration — how the commission-creation route couples fraud detection results with pre-existing partner-level groups to freeze a commission in-request

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** A conversion just triggered a fraud rule — where exactly does its commission get held, and which clawback/status inputs override the hold?

## Detect-then-hold inside createPartnerCommission, gated by plan and monitoring prerequisites
**Path/Symbol:** `apps/web/app/(ee)/api/workflows/create-partner-commission/route.ts` (:549-641 region; sole `detectAndRecordFraudEvent` call site).
**Signature:** inline block: `shouldRunRiskMonitoring = commission.customer && eventId && clickEvent` → `riskRulesTriggered = triggeredRules.length > 0`.
**Data Shape:** hold flip is a single guarded update `{ where: { id, status: pending }, data: { status: hold } }` with pre-picked `commissionBeforeHold {id, amount, earnings, status}` for the activity log.

### Decisive source
```ts
if (shouldRunRiskMonitoring) {
  const triggeredRules = await detectAndRecordFraudEvent({ program, partner,
    programEnrollment: pick(..., ["status","riskMonitoringDisabledAt"]),
    customer: { ..., ...(typeof isFirstConversion === "boolean" && { isFirstConversion }) },
    link, click: pick(clickEvent, ["url", "referer"]), event: { id: eventId } });
  riskRulesTriggered = triggeredRules.length > 0;
}
const { canManageFraudEvents } = getPlanCapabilities(program.workspace.plan);
if (canManageFraudEvents) {
  let shouldHoldCommission = false;
  if (riskRulesTriggered) shouldHoldCommission = true;
  else shouldHoldCommission = (await prisma.fraudEventGroup.findFirst({
        where: { programId, partnerId, status: pending, type: { in: PARTNER_LEVEL_FRAUD_RULES } }
      })) !== null;
  // An explicit `status` input (e.g. imports) wins; clawbacks (earnings <= 0) are never held.
  if (shouldHoldCommission && !status && commission.earnings > 0
      && commission.status === CommissionStatus.pending) {
    try { commission = await prisma.commission.update({ where: { id, status: pending },
           data: { status: hold }, include: commissionInclude });
          await trackCommissionStatusUpdate({ commissions: [commissionBeforeHold], newStatus: hold }); }
    catch { /* concurrent status change: refetch so side effects use DB truth */
            commission = await prisma.commission.findUniqueOrThrow({ where: { id }, include: commissionInclude }); }
  }
}
```
(create-partner-commission/route.ts :552-637 condensed)

**Flow:** run detection ONLY when customer+event+click all exist (monitoring needs full context) → hold if rules triggered THIS request OR any partner-level group already pends (dual-source hold — same predicate as `commission-hold-gating`) → overrides: explicit input `status` (imports pinning their own state), non-positive earnings (clawbacks), non-pending current status all skip the flip → failed guarded update ⇒ refetch instead of throwing, so downstream webhooks/postbacks see DB-truth state.
**Invariant:** (1) detection runs BEFORE the hold decision but its events are persisted independently — even a crashed hold leaves the fraud record for later group-based holds; (2) plan capability gates the HOLD, not the DETECTION (enterprise/advanced only freeze money; cheaper plans still record events); (3) `isFirstConversion` forwards ONLY when boolean (undefined never becomes false); (4) the catch-refetch keeps the "one write per status transition" contract intact under races.
**Probe:** anchored at dub repo root: `grep -o 'shouldRunRiskMonitoring' 'apps/web/app/(ee)/api/workflows/create-partner-commission/route.ts' | wc -l` = **2**; `grep -c 'detectAndRecordFraudEvent(' apps/web/app --include='*.ts' -r | grep -v ':0'` = exactly one call site (this route); `grep -c 'commission.earnings > 0' 'apps/web/app/(ee)/api/workflows/create-partner-commission/route.ts'` = **1**; `grep -c 'canManageFraudEvents: !!plan' apps/web/lib/plan-capabilities.ts` = **1**. Direct tests: E2E suites cover the triggered path via track endpoints (tests/fraud/*); the un-triggered partner-group branch shares logic audited at `commission-hold-gating`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "detectAndRecordFraudEvent", limit: 5 });
```

## Verdict
Adopt detect-before-create with dual-source hold and the three hold exemptions. Adapt plan gating. Omit the surrounding webhook fan-out (owned by other capsules).
