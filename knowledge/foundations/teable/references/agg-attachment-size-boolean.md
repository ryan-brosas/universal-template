<!-- capsule-v2 -->
# Attachment size nested-SUM + boolean containment — jsonb aggregate specials

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How are TotalAttachmentSize and checkbox Checked/UnChecked computed over jsonb cells?

## Per-row lateral SUM wrapped in outer SUM; @> '[true]'
**Path/Symbol:** `apps/nestjs-backend/src/db-provider/aggregation-query/postgres/aggregation-function.postgres.ts:totalAttachmentSize` (:42–50), `checked`/`unChecked`/`percentChecked`/`percentUnChecked` (:64–92); MCV boolean twins via `@> '[true]'::jsonb` in `multiple-value-aggregation.adapter.ts` (:82–110).
**Signature:** SQL text emitters; TotalAttachmentSize is on the compiler's `ignoreMcvFunc` list (computed per-row then summed).
**Data Shape:** attachment cell = jsonb array of `{size: number, ...}`; checkbox = scalar true/false or jsonb array of booleans.

### Decisive source
```ts
totalAttachmentSize(): string {
  return this.knex
    .raw(
      `SUM(COALESCE((SELECT SUM((e.value ->> 'size')::INTEGER)
        FROM jsonb_array_elements(COALESCE(${this.tableColumnRef}, '[]'::jsonb)) AS e), 0))`
    )
    .toQuery();
}
// MCV checked twin
checked(): string {
  return this.knex.raw(`SUM(CASE WHEN ${this.tableColumnRef} @> '[true]'::jsonb THEN 1 ELSE 0 END)`).toQuery();
}
```

**Flow:** Attachment sizes: per row, a correlated subquery iterates `jsonb_array_elements` summing each element's `size`; COALESCE('[]') makes empty arrays yield no rows so the inner SUM is NULL → COALESCE(...,0) → the OUTER SUM adds per-row totals across the group. Checkbox: containment `@> '[true]'` matches arrays containing true; unChecked counts `NULL OR NOT contains-true`.
**Invariant:** Two-porter traps: (1) the inner COALESCE must wrap the SUBQUERY not the cast — NULL rows have no elements, and only the outer-of-inner placement converts "no attachments" to additive 0 instead of poisoning SUM with NULL; (2) MCV unChecked counts NULL cells as unchecked (`IS NULL OR NOT ...`) but single-value unChecked counts only `false OR NULL` — merging them changes percentUnChecked denominators' meaning for never-touched checkboxes. The comment at `aggregation-function.abstract.ts:81` ("compute per-row then sum across group without MCV join") is why TotalAttachmentSize needs NO special adapter despite being an array func.
**Probe:** `grep -cF "jsonb_array_elements(COALESCE" apps/nestjs-backend/src/db-provider/aggregation-query/postgres/aggregation-function.postgres.ts` → 1; `grep -cF "@> '[true]'::jsonb" apps/nestjs-backend/src/db-provider/aggregation-query/postgres/multiple-value/multiple-value-aggregation.adapter.ts` → 4.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "totalAttachmentSize jsonb_array_elements checked unChecked", limit: 10 });
```

## Verdict
Adopt nested per-row→outer aggregation for array-of-objects metrics; adapt key names ('size') to your schema; keep containment operators for boolean-in-array semantics.
