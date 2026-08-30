<!-- capsule-v2 -->
# Validation-gate decision function — when does a measured search-path candidate earn confirmation?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How do timing A/B samples and plan evidence combine into a single ready/needs-validation/manual verdict?

## Correctness first, plan proof second, regression veto third
**Path/Symbol:** `packages/v2/table-query-ops/src/searchVectorValidation.ts` whole (58L): `chooseSearchAccessPathValidationNextAction` (:22-55), sample type (:6-17: legacy/candidate `{medianMs,p95Ms}`, `exactResultMatch`, planEvidence `{explainStatus, costBefore?, costAfter?, usesGinIndex, ginExpected}`); deprecated aliases (:19-20, :57-58).
**Signature:** `(samples) → 'ready_for_confirmation' | 'needs_plan_validation' | 'manual_investigation'`.
**Data Shape:** empty samples ⇒ needs_plan_validation; regression = candidate median > 1.2× legacy median (when legacy > 0).

### Decisive source
```ts
if (!samples.length) return 'needs_plan_validation';
if (samples.some(s => !s.exactResultMatch)) return 'manual_investigation';   // correctness veto FIRST
const indexed = samples.filter(s => s.planEvidence.ginExpected);
if (indexed.some(s => s.planEvidence.explainStatus !== 'validated'
    || !s.planEvidence.usesGinIndex
    || typeof s.costBefore !== 'number' || typeof s.costAfter !== 'number'))
  return 'needs_plan_validation';
const hasMaterialPlanImprovement = indexed.some(s => (s.costAfter ?? +Inf) < (s.costBefore ?? -Inf));
const hasMaterialTimingRegression = samples.some(s =>
  s.legacyPath.medianMs > 0 && s.candidatePath.medianMs > s.legacyPath.medianMs * 1.2);
return hasMaterialPlanImprovement && !hasMaterialTimingRegression
  ? 'ready_for_confirmation' : 'manual_investigation';
```

**Flow:** any result mismatch ⇒ manual (never auto-confirm a candidate that answers differently, regardless of speed) → expected-GIN samples missing validation/usage/numbers ⇒ needs_plan_validation (a measurement gap, retryable) → confirm only with BOTH a cheaper real plan AND no >20% timing regression.
**Invariant:** The three outcomes are semantically distinct: manual = evidence says NO; needs_plan_validation = evidence INSUFFICIENT; ready = all gates green. The Infinity defaults make the improvement check fail-closed on missing costs while the SOME-semantics lets one strongly-improving selective probe carry the set (short-probe fallback per spec).
**Probe:** `searchVectorValidation.spec.ts:25/:39/:45/:53/:57` — five direct specs incl. "never confirms a candidate with a different complete result set" and "allows a short-probe fallback".
**Coverage caveat:** none — pure function fully tested.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "chooseSearchAccessPathValidationNextAction exactResultMatch ginExpected", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the tri-state gate ordering (correctness → sufficiency → performance) verbatim; adapt thresholds (1.2×) to your SLO; omit nothing — this is a portable pure-function pattern.
