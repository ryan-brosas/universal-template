<!-- capsule-v2 -->
# Condition group evaluation — AND/OR semantics, undefined-field short-circuit, and highest-amount arbitration

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** How are modifier condition groups combined and which matching group wins when several match?

## Group loop with best-match sort
**Path/Symbol:** `apps/web/lib/partners/evaluate-reward-conditions.ts:evaluateRewardConditions` (:10-69) + local helpers `resolveConditionFieldValue` (:71-106), `evaluateCondition` (:108-224).
**Signature:** `evaluateRewardConditions({ conditions: RewardConditionsArray, context: RewardContext }): RewardConditions | null`.
**Data Shape:** conditions = array of groups `{operator: "AND"|"OR", type?, amountInCents?, amountInPercentage?, maxDuration?, conditions: RewardCondition[]}`; a condition = `{entity, attribute, operator, value, metadataField?}`.

### Decisive source
```ts
const conditionResults = conditionGroup.conditions.map((condition) => {
  const fieldValue = resolveConditionFieldValue({ condition, context });

  if (fieldValue === undefined) {
    return false;
  }

  return evaluateCondition({
    condition,
    fieldValue,
  });
});

// Apply the operator logic to the condition results
let conditionsMet = false;
if (conditionGroup.operator === "AND") {
  conditionsMet = conditionResults.every((result) => result);
} else if (conditionGroup.operator === "OR") {
  conditionsMet = conditionResults.some((result) => result);
}
```
(evaluate-reward-conditions.ts :25-44)

**Flow:** per group: resolve each condition's field value → `undefined` (missing entity/attribute or rejected metadata key) SHORT-CIRCUITS that condition to false BEFORE operator logic → AND = every, OR = some → collect matched groups → empty ⇒ null → else sort ALL matched groups by `getRewardAmount({type: b.type!, ...}) − getRewardAmount({...a})` descending and return `[0]` — the highest-paying match wins regardless of declaration order.
**Invariant:** an unknown group operator (neither AND nor OR) leaves `conditionsMet=false`; the winner is chosen by computed reward amount, NOT first-match — the reward-conditions.test.ts "should return first matching condition group" test (:252-306) passes only because its single matching group is also the highest; a porter who switches to first-match changes payout outcomes whenever two groups match. Note `b.type!` non-null assertion in the comparator — a type-less matched group sorts as flat-cents 0.
**Probe:** deterministic probes (repo root): `grep -n 'conditionGroup.operator === "AND"' apps/web/lib/partners/evaluate-reward-conditions.ts` → :40; `grep -n 'fieldValue === undefined' apps/web/lib/partners/evaluate-reward-conditions.ts` → :28; `grep -n 'matchingConditions.length === 0' apps/web/lib/partners/evaluate-reward-conditions.ts` → :51; `grep -c 'getRewardAmount' apps/web/lib/partners/evaluate-reward-conditions.ts` → 3 (import + two comparator arms). Direct tests: `apps/web/tests/rewards/reward-conditions.test.ts` (2,484L, ~90 tests incl. AND/OR/multi-group/operator matrices + edge cases) — vitest offline-blocked (standing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "evaluateRewardConditions", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt undefined-short-circuit-before-operator, every/some mapping, and amount-descending winner selection. Adapt the condition schema. Omit nothing.
