<!-- capsule-v2 -->
# Same-table CTE formula batching — how do many same-table formula recomputes compile into level-ordered CTEs with shared-subexpression reuse?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How is a batch of same-table formula updates turned into one statement without re-evaluating identical subexpressions?

## SQL plan objects: fragments → CSE bindings → leveled CTEs
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/computed/SameTableBatchSqlPlan.ts` (143L) + builder `SameTableBatchQueryBuilder.ts` (838L); direct tests `SameTableBatchQueryBuilder.spec.ts`, `__tests__/SameTableBatch.spec.ts`.
**Signature:** `FormulaFieldSqlFragment.create({ fieldId, columnAlias, expressionSql, errorConditionSql?, cseEligible })`; `CteLevelSqlPlan.create({ name, level, previousCteName?, fragments }, cseBindings)`; `FormulaCseBinding` keyed by `normalizeExpressionKey` (whitespace-collapsed SQL text).
**Data Shape:** error companion columns aliased `__err_<columnAlias>` (`errorColumnAlias`).

### Decisive source
```ts
// CSE identity = normalized SQL text, not field id
const normalizeExpressionKey = (sqlText: string): string =>
  sqlText.replace(/\s+/g, ' ').trim();
// binding renders once in its CTE level, referenced as "__cse".<alias>
selectItemSql(): string  { return `(${this.expressionSql}) as "${this.alias}"`; }
referenceSql(cseAlias = '__cse'): string { return `"${cseAlias}"."${this.alias}"`; }
```

**Flow:** planner groups same-table formulas by dependency LEVEL; each level becomes one CTE selecting prior level via `previousCteName`; eligible fragments sharing a normalized key collapse into a single `FormulaCseBinding` computed once per level and referenced by every dependent fragment; per-field error conditions project alongside values so failures degrade per-cell, not per-statement.

**Invariants:**
1. CSE dedup is TEXT-normalized — two fields with byte-identical expressions share evaluation even when their ids differ; whitespace differences must NOT split the binding.
2. Levels chain strictly through previousCteName; cross-level references go through named CTEs, never lateral re-evaluation.
3. Error columns travel WITH their value columns so a poisoned formula cannot abort the batch.

**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/computed/SameTableBatchQueryBuilder.spec.ts` (CTE shape assertions); integration twin `__tests__/SameTableBatch.spec.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "FormulaCseBinding CteLevelSqlPlan", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt normalized-key CSE and level-chained CTEs for bulk formula math. Adapt alias conventions to your SQL style. Omit the query-builder's plan-derivation internals if you only need the shape contract.
