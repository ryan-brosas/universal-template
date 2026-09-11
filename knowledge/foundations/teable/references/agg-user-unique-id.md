<!-- capsule-v2 -->
# User-family unique-by-id aggregation — why Unique extracts ->> 'id' only for single user fields

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What does "unique count" mean for a User/CreatedBy/LastModifiedBy column stored as jsonb `{id, title}`?

## Type-gated DISTINCT extraction
**Path/Symbol:** `apps/nestjs-backend/src/db-provider/aggregation-query/postgres/aggregation-function.postgres.ts:unique` (:6–16) and `percentUnique` (:18–32).
**Signature:** overrides of the abstract defaults; branch on `[User, CreatedBy, LastModifiedBy].includes(type) && !isMultipleCellValue`.
**Data Shape:** user cells are jsonb objects `{"id": "...", "title": "..."}`; MCV variants are arrays of them.

### Decisive source
```ts
unique(): string {
  const { type, isMultipleCellValue } = this.field;
  if (![FieldType.User, FieldType.CreatedBy, FieldType.LastModifiedBy].includes(type) ||
      isMultipleCellValue) {
    return super.unique();   // COUNT(DISTINCT col)
  }
  return this.knex.raw(`COUNT(DISTINCT ${this.tableColumnRef} ->> 'id')`).toQuery();
}
```

**Flow:** For a SINGLE-valued user-family field: uniqueness = distinct person ids (`->> 'id'`). Everything else (plain text/number columns, multi-value collaborators) falls back to whole-cell DISTINCT.
**Invariant:** Whole-cell DISTINCT on a jsonb object would treat two rows as unique if ANY display metadata differs (title re-render), inflating counts; id-extraction defines uniqueness by identity. But for MULTI-valued user cells the fallback is deliberate — element-level distinct would need the MCV join and count people-per-element, which is NOT what the grid chip promises; the valid-func table (`getValidStatisticFunc` drops Unique when `isMultipleCellValue`) already keeps this combination unreachable through the API. Porters who "fix" the asymmetry by always extracting id change semantics for collaborator fields.
**Probe:** `grep -cF "->> 'id'" apps/nestjs-backend/src/db-provider/aggregation-query/postgres/aggregation-function.postgres.ts` → 3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "AggregationFunctionPostgres unique percentUnique user id distinct", limit: 10 });
```

## Verdict
Adopt identity-keyed distinct for person/reference columns; adapt the extraction key to your schema; omit the multi-value carve-out if your API forbids that combination.
