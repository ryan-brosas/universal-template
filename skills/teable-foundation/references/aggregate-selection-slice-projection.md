<!-- capsule-v2 -->
# aggregate-selection-slice-projection — How do aggregates avoid generating CTEs for fields the aggregation never touches?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What does buildAggregateSelect select, given there is no row-level SELECT list?

## Visitor runs for side effects only: selectionMap entries + CTE generation for aggregation/group/filter-referenced ids
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts:buildAggregateSelect` (:683-714) + `getReadyLinkFieldIds` (:619-631).
**Signature:** `private buildAggregateSelect(qb, table, state, projection?, preferStoredLookupFields?)` — visitor results are DISCARDED (`field.accept(visitor);` without select()).
**Data Shape:** orderedFields = getOrderedFieldsByProjection(projection, expand=true); readyLinkFieldIds derived from manager's joined CTEs so visitors only reference already-emitted link CTEs.

### Decisive source
```ts
// Add field-specific selections using visitor pattern. Aggregations only need
// selections for fields referenced by aggregation/group/search/filter callers.
const orderedFields = getOrderedFieldsByProjection(table, projection, true) as FieldCore[];
for (const field of orderedFields) {
  field.accept(visitor);   // result intentionally unused
}
```

**Flow:** createQueryBuilder already built link/conditional CTEs for the projection closure → buildAggregateSelect re-walks fields so each computed field REGISTERS its expression in selectionMap → aggregation/group builders compile statistic expressions against that map → no per-field qb.select() ever happens (aggregates have their own alias scheme `<fieldId>_<func>`).
**Invariant:** the same visitor serves SELECT-list and registration-only modes — a porter who "simplifies" the discarded accept() call silently loses filter/sort expression resolution for aggregate queries. preferStoredLookupFields defaults TRUE here (unlike record lists), reading persisted columns instead of expanding CTEs.
**Probe:** static byte-exact: `grep -n 'field.accept(visitor);' apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts` → :709 region with its two-line comment.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"buildAggregateSelect","limit":3,"detail":"ids"}'
```

## Verdict
Adopt registration-only visiting for aggregate paths. Adapt default flags. Omit nothing.
