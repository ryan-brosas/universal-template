<!-- capsule-v2 -->
# formula-expansion-context-swap — How are nested formula references expanded in SELECT SQL without corrupting per-field type/timezone context?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What does the expansion cache + stack + save/restore trio guarantee?

## Cache results, throw on cycles, restore targetDbFieldType/timeZone after each expansion
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/sql-conversion.visitor.ts:expandFormulaField` (:425-499).
**Signature:** `protected expandFormulaField(fieldId, fieldInfo: IFieldWithExpression): string`.
**Data Shape:** `context.expansionCache: Map<fieldId, sql>`; `expansionStack: Set` (cycle detector); selectContext carries `targetDbFieldType` + `timeZone`, both saved before recursion and restored in `finally`.

### Decisive source
```ts
if (this.expansionStack.has(fieldId)) {
  throw new CircularReferenceError(fieldId, Array.from(this.expansionStack));
}
...
if (selectContext) {
  if (nextTargetDbFieldType != null) selectContext.targetDbFieldType = nextTargetDbFieldType;
  if (nextTimeZone != null) selectContext.timeZone = nextTimeZone;
}
try {
  const tree = parseFormula(expression);
  const expandedSql = tree.accept(this);
  this.context.expansionCache.set(fieldId, expandedSql);
  return expandedSql;
} finally {
  if (selectContext) {
    selectContext.targetDbFieldType = prevTargetDbFieldType;
    selectContext.timeZone = prevTimeZone;
  }
  this.expansionStack.delete(fieldId);
}
```

**Flow:** formula reference in a `{field}` slot → if the target is itself a formula needing expansion → cache hit returns immediately → stack membership means circular definition (typed error carrying the chain) → otherwise parse the nested expression and visit it with THIS visitor while the conversion CONTEXT is temporarily switched to the nested field's own dbFieldType/timeZone (read even from JSON-string options) → restore unconditionally.
**Invariant:** without the save/restore, an outer numeric formula containing an inner date formula would keep the inner's DateTime target type for its own remaining operators — silent wrong casts. The cache makes repeated references to one field expand once.
**Probe:** upstream direct spec `formula-support-generated-column-validator.spec.ts` pins the sibling validator over the same AST; static probe byte-exact: `grep -n 'prevTargetDbFieldType' sql-conversion.visitor.ts` → :455/:491; `grep -n 'CircularReferenceError' sql-conversion.visitor.ts` → :441.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"expandFormulaField","limit":3,"detail":"ids"}'
```

## Verdict
Adopt cache+stack+save/restore wholesale for any recursive expression expander. Adapt error type. Omit nothing.
