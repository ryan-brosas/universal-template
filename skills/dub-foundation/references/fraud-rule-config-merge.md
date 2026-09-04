<!-- capsule-v2 -->
# Program-over-global fraud rule merge — how do program overrides compose with global defaults, and what is the enabled-state of a rule with NO override row?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** When a program has no FraudRule row for a type, is that rule on or off — and which fields come from the global catalog vs the override?

## Global catalog iterated, program rows looked up per type
**Path/Symbol:** `apps/web/lib/api/fraud/get-merged-fraud-rules.ts:getMergedFraudRules` (:7-40) + `isFraudRuleEnabled` (:42-53).
**Signature:** `function getMergedFraudRules(programRules: FraudRule[]): FraudRuleProps[]`; `function isFraudRuleEnabled({ fraudRules, ruleType }): boolean`.
**Data Shape:** iteration driver = `CONFIGURABLE_FRAUD_RULES` (the 6 `configurable: true` entries of the static `FRAUD_RULES` catalog in constants.ts :286-288). Output rows: `{id: string|undefined, name/description/type: FROM GLOBAL CATALOG, config: programRule.config ?? undefined, enabled}`.

### Decisive source
```ts
CONFIGURABLE_FRAUD_RULES.forEach((globalRule) => {
  const programRule = programRules.find((r) => r.type === globalRule.type);
  if (programRule) {
    mergedRules.push({ id: programRule.id, name: globalRule.name,
      description: globalRule.description, type: globalRule.type,
      config: programRule.config ?? undefined,
      enabled: programRule.disabledAt === null });   // override present → disabledAt decides
    return;
  }
  mergedRules.push({ id: undefined, ..., config: undefined,
    enabled: true });                                 // NO override → ENABLED BY DEFAULT
});
```
(get-merged-fraud-rules.ts :10-37 condensed)

**Flow:** for each configurable global type → first matching program row wins → merge display metadata from catalog + operational state from DB. `isFraudRuleEnabled` re-runs the same merge and defaults to **true** when the queried type isn't found in merged output (e.g. non-configurable types like `partnerEmailMasked` are always "enabled" — they have no toggle).
**Invariant:** (1) absence-of-row means ON, not off — programs opt OUT by creating a disabled row (`disabledAt != null`), never opt in; (2) `name`/`description` ALWAYS come from code, so UI copy can't be edited via DB; (3) only CONFIGURABLE rules participate — the four non-configurable partner risks (email masked/domain mismatch/no social/no verified) are computed live at read time and ignore this table entirely; (4) `config` passes through raw (`?? undefined`) — schema validation happens inside each rule's evaluate.
**Probe:** anchored at dub repo root: `grep -c 'disabledAt === null' apps/web/lib/api/fraud/get-merged-fraud-rules.ts` = **1**; `grep -c 'enabled: true' apps/web/lib/api/fraud/get-merged-fraud-rules.ts` = **1** (the no-override branch); `grep -c 'programRule.type === globalRule.type' apps/web/lib/api/fraud/get-merged-fraud-rules.ts` = **1**. Direct tests: none isolated (caveat); exercised indirectly by every E2E fraud flow.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getMergedFraudRules", limit: 5 });
```

## Verdict
Adopt the opt-out-by-disabled-row merge with catalog-owned copy. Adapt rule-type enums/config shapes. Omit the FraudRuleProps type gymnastics.
