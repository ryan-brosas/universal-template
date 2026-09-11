<!-- capsule-v2 -->
# filter-augmented-selection — How can a WHERE clause reference fields that the SELECT never projected?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What selectionMap does the filter compiler receive when projection is narrower than the filter?

## Augment the collected selection map with alias-qualified physical columns for ALL fields
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts:buildFilter` (:716-752, augment at :735-740).
**Signature:** `private buildFilter(qb, table, filter, selectionMap: IReadonlyRecordSelectionMap, currentUserId?, mainAlias?)`.
**Data Shape:** copies the visitor-collected map (field-id → SQL expression) into `augmentedSelection`, then ADDS every field of the table as `"alias"."dbFieldName"` qualified refs; field lookup map keys BOTH id and name.

### Decisive source
```ts
// Allow filters to reference fields even if they are not part of the final projection
// so that permission-hidden fields can still participate in WHERE clauses.
const augmentedSelection = new Map(selectionMap);
if (mainAlias) {
  table.fieldList.forEach((field) => {
    const qualified = this.knex.ref(`${mainAlias}.${field.dbFieldName}`).toQuery();
    augmentedSelection.set(field.id, qualified);
  });
}
```

**Flow:** buildSelect populates selectionMap only for projected fields → buildFilter clones it → unconditional per-field augmentation OVERWRITES each id with a plain physical reference (computed fields included — their CTE expressions are replaced by raw columns for filtering) → dbProvider.filterQuery consumes the augmented map.
**Invariant:** filter compilation must never fail on "selection missing" — after augmentation every table field resolves. Note the deliberate consequence: hidden-but-filterable fields keep working; and sort uses the OPPOSITE policy (see sort-selection-gate) — filter augments, sort restricts.
**Probe:** static: `grep -n 'augmentedSelection.set(field.id, qualified)' ...service.ts` → :738 with the allow-comment at :733-734.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"buildFilter augmentedSelection","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the clone-then-augment pattern whenever one selectionMap serves both SELECT and WHERE. Adapt qualification style to your knex/dialect. Omit nothing.
