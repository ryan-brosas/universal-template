<!-- capsule-v2 -->
# projection-dependency-closure — How is the projected field set expanded to the fields its CTEs actually need?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Given `projection: [lookupFieldId]`, which additional fields must enter CTE generation and SELECT?

## BFS closure: lookup/rollup pull their link field; formulas pull reference fields (toggleable); order preserved
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/record-query-builder.util.ts:getOrderedFieldsByProjection` (:40-100) + `getTableAliasFromTable` (:14-20) + `getLinkUsesJunctionTable` (:22-28).
**Signature:** `getOrderedFieldsByProjection(table, projection?: string[], expandFormulaReferences = true): FieldCore[]`.
**Data Shape:** empty/undefined projection → ALL ordered fields; wanted-set seeded with projection ids; queue-driven expansion; output filtered back into `table.fields.ordered` order.

### Decisive source
```ts
if (field.isLookup || field.type === FieldType.Rollup || field.type === FieldType.ConditionalRollup) {
  const link = field.getLinkField(table);
  if (link && !wanted.has(link.id)) { wanted.add(link.id); queue.push(link.id); }
  continue;
}
if (field.type === FieldType.Formula) {
  if (!expandFormulaReferences) continue;
  if (visitedFormula.has(field.id)) continue;
  visitedFormula.add(field.id);
  for (const rf of (field as FormulaFieldCore).getReferenceFields(table)) { … }
}
```

**Flow:** seed → pop id → link fields add nothing → computed fields enqueue their LINK dependency → formulas recursively enqueue referenced fields unless `expandFormulaReferences=false` (the flag that makes raw-propagation contexts cheap and keeps formula SQL from exploding) → final list re-sorted to table-declared order.
**Invariant:** the closure runs BEFORE CTE generation so a lookup can be selected while its link field is absent from the user-facing SELECT (`build()` iterates this same list to pre-generate link CTEs "even when the link fields themselves are not part of the projection"). Alias derivation `t_<sanitizedTableId>` guarantees aliases never collide with physical names truncated at 63 chars.
**Probe:** static byte-exact: `grep -n 'expandFormulaReferences' record-query-builder.util.ts` → :40/:66/:69/:96 region; upstream spec `record-query-builder-group-quoting.spec.ts` exercises projection-narrowed aggregates end-to-end.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"getOrderedFieldsByProjection","limit":3,"detail":"ids"}'
```

## Verdict
Adopt closure-before-build + order preservation. Adapt the toggle. Omit nothing.
