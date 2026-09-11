<!-- capsule-v2 -->
# Modifier override merge — which fields does a matched condition override, and what do null vs undefined mean?

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** When a reward modifier's conditions match, exactly how is the base reward mutated — and why does `amountInCents` become null instead of staying absent?

## Matched-condition field overlay
**Path/Symbol:** `apps/web/lib/partners/determine-partner-reward.ts:determinePartnerReward` modifier branch (:65-97).
**Signature:** input `partnerReward.modifiers` parsed via `rewardConditionsArraySchema.safeParse`; output a shallow-copied Reward with up to four overridden fields.
**Data Shape:** modifiers parse-failure is SILENTLY ignored (base reward stands); `matchedCondition.type` may be undefined; amounts use `!= null` (null OR undefined) tests; `maxDuration` uses `!== undefined` — three different absence semantics in ten lines.

### Decisive source
```ts
if (modifiers.success) {
  const matchedCondition = evaluateRewardConditions({
    conditions: modifiers.data,
    context,
  });

  if (matchedCondition) {
    partnerReward = {
      ...partnerReward,
      // Override the reward amount, type and max duration with the matched condition
      type: matchedCondition.type || partnerReward.type,
      amountInCents:
        matchedCondition.amountInCents != null
          ? matchedCondition.amountInCents
          : null,
      amountInPercentage:
        matchedCondition.amountInPercentage != null
          ? new Prisma.Decimal(matchedCondition.amountInPercentage)
          : null,
      maxDuration:
        matchedCondition.maxDuration !== undefined
          ? matchedCondition.maxDuration
          : partnerReward.maxDuration,
    };
  }
}
```
(determine-partner-reward.ts :71-95)

**Flow:** safeParse modifiers → evaluate all condition groups → first (highest-amount) match wins → overlay: `type` falls back on falsy, both amount fields are FORCED to an explicit `null` when the condition doesn't carry them (so a flat condition clears percentage and vice-versa — no stale carry-over from the base reward), percentage wraps through `new Prisma.Decimal` to satisfy the column type, `maxDuration` preserves the base unless explicitly defined.
**Invariant:** after a matched-modifier override, exactly ONE of amountInCents/amountInPercentage can be non-null; a porter who keeps the base reward's amount when the condition lacks one ships double-paying rewards. The explicit-null clear is the whole point of this shape.
**Probe:** deterministic probes (repo root): `grep -n 'amountInCents != null' apps/web/lib/partners/determine-partner-reward.ts` → :83; `grep -n 'maxDuration !== undefined' apps/web/lib/partners/determine-partner-reward.ts` → :91; `grep -n 'new Prisma.Decimal' apps/web/lib/partners/determine-partner-reward.ts` → :88; `grep -c 'safeParse' apps/web/lib/partners/determine-partner-reward.ts` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "determinePartnerReward", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-field overlay with its three distinct absence semantics (falsy-type, null-clearing amounts, undefined-preserving maxDuration). Adapt the Decimal wrapper to your money type. Omit nothing here — every branch is load-bearing.
