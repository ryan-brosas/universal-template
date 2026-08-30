<!-- capsule-v2 -->
# Null-Equivalent Filter Widening — where do empty-string/empty-array ≈ NULL semantics enter filters, and exactly how?

**Source:** twenty-crm AGPL-3.0 `main@9e4717278c29efa3ba0c147f6acf0d68e99a625c`; Codebase Memory `twenty-crm`. **Question:** If the write path normalizes `''` and `[]` to SQL NULL for TEXT-like/ARRAY-like columns, how must `eq`, `neq`, and `is` filters widen so `{eq: ""}` still matches rows whose value was stored as NULL?

## Type × subFieldKey matrix deciding the widening arm
**Path/Symbol:** `packages/twenty-server/src/engine/api/common/common-args-processors/data-arg-processor/utils/find-postgres-default-null-equivalent-value.util.ts` : `findPostgresDefaultNullEquivalentValue` (lines 10–147); widening applied in `compute-where-condition-parts.ts` (lines 46–162).
**Signature:** `findPostgresDefaultNullEquivalentValue(value: unknown, fieldMetadataType: FieldMetadataType, key?: string): unknown | undefined` — returns the Postgres null-equivalent constant or `undefined` (no widening).
**Data Shape:** constants (`null-equivalent-values.constant.ts`): text ≈ `''` (`POSTGRES_DEFAULT_TEXT_FIELD_NULL_EQUIVALENT_VALUE`), array ≈ `'{}'` (`POSTGRES_DEFAULT_ARRAY_FIELD_NULL_EQUIVALENT_VALUE`); predicates treat `null` itself as null-equivalent too.

### Decisive source
```ts
// compute-where-condition-parts.ts — how the equivalent is spliced into each operator:
case 'eq':
  return {
    sql: `${fieldReference} = :${key}${paramSuffix}${hasNullEquivalentFieldValue ? ` OR ${fieldReference} IS NULL` : ''}`,
    params: { [`${key}${paramSuffix}`]: value },
  };
case 'neq':
  return {
    sql: `${fieldReference} != :${key}${paramSuffix}${hasNullEquivalentFieldValue ? ` AND ${fieldReference} IS NOT NULL` : ''}`,
    ...
  };
case 'is':
  return {
    sql: `${fieldReference} IS ${value === 'NULL' ? 'NULL' : 'NOT NULL'}${hasNullEquivalentFieldValue ? ` OR ${fieldReference} = :${key}${secondParamSuffix}` : ''}`,
    params: hasNullEquivalentFieldValue ? { [`${key}${secondParamSuffix}`]: nullEquivalentFieldValue } : {},
  };

// find-postgres-default-null-equivalent-value.util.ts — which (type, subField) pairs widen:
case FieldMetadataType.TEXT:
  return isNullEquivalentTextFieldValue(value) || value === 'NULL'
    ? POSTGRES_DEFAULT_TEXT_FIELD_NULL_EQUIVALENT_VALUE : undefined;
case FieldMetadataType.EMAILS: {
  switch (key) {
    case 'primaryEmail':    /* text-equivalent */ ...
    case 'additionalEmails': /* array-equivalent */ ...
```

**Flow:** before compiling any comparison, ask the matrix whether THIS (field type, sub-field key) pair has a stored-as-null empty value → if yes: `eq` widens with `OR IS NULL`; `neq` NARROWS with `AND IS NOT NULL` (negation must stay the exact complement of the widened eq); `isEmptyArray` gains `OR IS NULL`; `is NULL` gains `OR = ''`; like/ilike gain `OR IS NULL`. The literal string `'NULL'` in filter input is treated as an explicit null request.
**Invariant:** widened `eq` and narrowed `neq` must remain exact logical complements over the physical column domain — that is why neq gets `AND IS NOT NULL` rather than nothing. Widening is per-sub-field precise: `emails.primaryEmail` widens as text while `emails.additionalEmails` widens as array; scalar numeric/date types never widen.
**Probe:** direct source read this pass of both files; the strict-twin spec (`compute-cursor-arg-filter.utils.spec.ts:266–274`) pins the complementary no-widening shapes. RUNNER BLOCKED (jest unavailable).

## Get live surrounding code
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "twenty-crm", query: "findPostgresDefaultNullEquivalentValue null equivalent empty string array widening filter", limit: 6, fields: ["signature"] });
// → findPostgresDefaultNullEquivalentValue 10-147 (rank 1), isNullEquivalentArrayFieldValue (rank 2),
//   workflow twin findDefaultNullEquivalentValue (rank 3 — duplicated logic in workflow executor)
```

## Verdict
Adopt the complement-pair widening algebra (eq∪NULL / neq∩NOT NULL) driven by a type×sub-field matrix mirroring the write-side normalization. Adopt treating the literal 'NULL' input as explicit null. Adapt the matrix to your own write-normalization rules — it must be derived from them, never hand-guessed. Omit for stores where empty values stay empty. Note upstream duplicates this matrix inside the workflow-executor filter utils — port one shared copy.
