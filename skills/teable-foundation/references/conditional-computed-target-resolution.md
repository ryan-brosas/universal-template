<!-- capsule-v2 -->
# conditional-computed-target-resolution — How does a filter/sort inside a conditional rollup reference ANOTHER computed field on the foreign table?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** When the conditional filter targets a nested ConditionalRollup/ConditionalLookup, what expression replaces the physical column?

## Generate-or-reuse the nested CTE, then scalar-subquery it by foreign record id; degrade to selectVisitor SQL
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/field-cte-visitor.ts:resolveConditionalComputedTargetExpression` (:1233-1275) + `coerceConditionalLookupTargetExpression` (:1276-1291).
**Signature:** `resolveConditionalComputedTargetExpression(targetField: FieldCore, foreignTable, foreignAlias, selectVisitor): string`.
**Data Shape:** nested CTE read shape: `((SELECT "conditional_rollup_<id>" FROM "<cte>" WHERE "<cte>"."main_record_id" = "<foreignAlias>"."__id"))`; expandFormulaReferences=false short-circuits computed families to physical columns.

### Decisive source
```ts
if (targetField.type === FieldType.ConditionalRollup) {
  this.generateConditionalRollupFieldCteForScope(foreignTable, targetField);
  const nestedCteName = this.getCteNameForField(conditionalTarget.id);
  if (nestedCteName) {
    return `((SELECT "conditional_rollup_${id}" FROM "${nestedCteName}"
            WHERE "${nestedCteName}"."main_record_id" = "${foreignAlias}"."${ID}"))`;
  }
  const fallback = conditionalTarget.accept(selectVisitor);
  return this.unwrapSelectName(fallback);   // inline SQL when CTE could not be made
}
```

**Flow:** resolve target → ensure its CTE exists in CURRENT scope (scope-aware variants take an explicit table arg) → wrap value in a correlated scalar subquery keyed on the foreign alias's record id → coercion pass casts numeric/boolean cell types for lookup targets (multi-value and conditional-lookups exempt) → CTE-less fallback compiles through FieldSelectVisitor instead.
**Invariant:** generation happens against the FOREIGN table scope so names/aliases match the enclosing counts query; the double-parenthesized scalar subquery is required wherever PG expects one value (filter comparands). The expandFormulaReferences=false escape hatch exists for raw-propagation contexts (UPDATE ... FROM) where CTE recursion would be unsound.
**Probe:** static byte-exact: `grep -n 'resolveConditionalComputedTargetExpression' field-cte-visitor.ts` → definition :1233 + call sites :866/:1379/:1745/:1786.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"resolveConditionalComputedTargetExpression","limit":3,"detail":"ids"}'
```

## Verdict
Adopt ensure-CTE→scalar-subquery→fallback ordering. Adapt id column naming. Omit nothing.
