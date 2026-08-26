<!-- capsule-v2 -->
# Payout eligibility & effective mode — how does one predicate decide which payouts a program can pay, and why must read-side mode derivation mirror it?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What exactly makes a payout "eligible" per payoutMode, and how do hybrid programs resolve a row's mode when the stored column is null?

## getPayoutEligibilityFilter + getEffectivePayoutMode: mode-branched WHERE + derived fallback
**Path/Symbol:** `apps/web/lib/api/payouts/payout-eligibility-filter.ts:getPayoutEligibilityFilter` (:8-66); `apps/web/lib/api/payouts/get-effective-payout-mode.ts:getEffectivePayoutMode` (:10-19); Tremendous bounds `apps/web/lib/tremendous/constants.ts:2-3` ($5 / $2000).
**Signature:** `getPayoutEligibilityFilter({ program: Pick<Program,"id"|"minPayoutAmount"|"payoutMode"> }): Prisma.PayoutWhereInput`; `getEffectivePayoutMode({ payoutMode, payoutsEnabledAt }): PayoutMode`.
**Data Shape:** commonWhere = `{programId, status:"pending", invoiceId:null, amount:{gte:minPayoutAmount}, NOT:{partner.defaultPayoutMethod:"tremendous" ∧ (amount<$500 OR amount>$200000)}}` — the Tremendous gift-card window is expressed as a NOT of an OR, not two negations.

### Decisive source
```ts
switch (program.payoutMode) {
  case "internal": return { ...commonWhere,
    partner: { payoutsEnabledAt: { not: null } } };
  case "external": return { ...commonWhere,
    programEnrollment: { tenantId: { not: null } } };
  case "hybrid":   return { ...commonWhere, OR: [
    { partner: { payoutsEnabledAt: { not: null } } },
    { programEnrollment: { tenantId: { not: null } } }] };
  default: throw new Error(`Unsupported payout mode: ${program.payoutMode}`);
}
```
(:33-65)
```ts
case "hybrid": return payoutsEnabledAt === null ? "external" : "internal";
default: throw new Error(`Invalid payout mode: ${payoutMode}`);
```
(get-effective-payout-mode :14-17)

**Flow:** the filter is THE single predicate consumed by confirm-payouts' cutoff count, getEligiblePayouts, splitPayouts, and processPayouts' claim — one definition, five consumers. Read side (`get-payouts.ts:151-158`, `get-eligible-payouts.ts:87-95`, single `[payoutId]` route :186-192) recomputes `mode = payout.mode ?? getEffectivePayoutMode(...)` for rows persisted before the column existed, and projects `traceId ← stripePayoutTraceId` plus `tenantId/groupId` from the enrollment join.
**Invariant:** (1) internal ⇒ partner has completed payout onboarding (`payoutsEnabledAt`), external ⇒ enrollment carries an integration `tenantId`; hybrid is an OR at write time but resolves PER PARTNER at read time via the same two fields — flipping either field changes classification without any row rewrite; (2) `invoiceId:null` keeps claimed payouts out of every later eligibility scan; (3) gift-card (Tremendous) amounts are range-gated inside the shared WHERE so ineligible rows never even enter a claim; (4) unknown payoutMode throws rather than defaulting.
**Probe:** deterministic probe: `grep -c 'payoutsEnabledAt: {' apps/web/lib/api/payouts/payout-eligibility-filter.ts` = 3; `grep -n 'tenantId_programId\|resolvePartnerId' apps/web/lib/api/payouts/get-payouts.ts | head -2` = :68,:109. No direct unit suite (recorded caveat; behavior pinned by cross-capsule grep battery).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getPayoutEligibilityFilter", limit: 5 });
```

## Verdict
Adopt the three-mode predicate + derived-mode read fallback as a pair — porting one without the other silently misclassifies legacy rows. Adapt the mode enum and onboarding markers. Omit the Tremendous window if you have no gift-card rail (but keep the pattern: provider-specific amount windows belong INSIDE the shared eligibility predicate).
