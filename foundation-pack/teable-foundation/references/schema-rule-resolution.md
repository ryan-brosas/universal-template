<!-- capsule-v2 -->
# Rule resolution ladder — how do you order, validate, and invert a set of dependent DDL rules without executing anything?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** Where does topological ordering happen and why must validation stay sequential per rule?

## SchemaRuleResolver (Kahn) + SchemaRulePlanner (targeting)
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/resolver/SchemaRuleResolver.ts` — `resolve` (:61–126), `validateAll` (:128–144), `upAll` (:146–162), `downAll` (:164–182); planner `rules/planner/SchemaRulePlanner.ts` — `planTable` (:196–329), `collectDependencyClosure` (:132–154), `calculateRuleDepths` (:80–117).
**Signature:** `resolve(rules): Result<{orderedRules}, DomainError>`; `planTable(table, target?: {fieldId?, ruleId?}): ReadonlyArray<SchemaRulePlanEntry>` where entry is `{type:'error', fieldId, fieldName, stage: 'field_lookup'|'rule_lookup'|'rules_creation'|'rules_resolution', message}` or `{type:'plan', ctx, orderedRules, selectedRules, ruleDepths}`.
**Data Shape:** edges only count dependencies present IN the current rule set (dangling ids silently ignored); depths = longest dependency chain via memoized DFS with a fresh visited-set per path.

### Decisive source
```ts
// dangling dependency tolerance — external rules are NOT errors
for (const depId of rule.dependencies) {
  if (ruleMap.has(depId)) {           // ← only in-set deps become edges
    graph.get(depId)!.push(rule.id);
    inDegree.set(rule.id, (inDegree.get(rule.id) ?? 0) + 1);
  }
}
// cycle detection AFTER the sort: leftover nodes = cycle members, named in the error
if (sorted.length !== rules.length) { /* err 'Circular dependency detected among rules: ...' */ }

// downAll = resolve again then REVERSE the same order
const reversedRules = [...resolution.orderedRules].reverse();
```

**Flow:** planner resolves table location from the aggregate (`dbTableName().split({defaultSchema})`, falling back to `{schema: defaultSchema, tableName: tableId}` on ANY error) → prepends system-table rules under pseudo-field `__system__` unless targeting one specific field → per field builds rules + resolves → `createPlanEntry` narrows to `selectedRules` = ruleId target + its full dependency closure → checker/repairer consume plan entries; every failure becomes a typed plan-error entry with its stage, never a throw.
**Invariant:** `upAll` order = topo order; `downAll` order = exact reverse; validation runs in dependency order so dependents see parents' results; ruleId targeting WITHOUT fieldId is rejected up front ('ruleId targeting requires fieldId').
**Probe:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/resolver/SchemaRuleResolver.spec.ts:47 'should detect circular dependencies'`, :66 'should ignore dependencies not in the rule set', :97/:109 upAll/downAll ordering.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "SchemaRuleResolver resolve Kahn circular dependency SchemaRulePlanner planTable", limit: 10 });
```

## Verdict
Adopt resolve-once/reuse-for-up-and-down, reverse-for-teardown, closure-based single-rule targeting, stage-tagged plan errors, and dangling-dependency tolerance; adapt the pseudo-field `__system__` convention; omit teable's sessionCache threading if you have no cross-table lookups to amortize.
