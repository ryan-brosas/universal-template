<!-- capsule-v2 -->
# flatten-nested-json-array — How are arrays-of-arrays lookup payloads flattened for consumers expecting one level?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What recursive SQL flattens `lookup-of-lookup` results, and when is it skipped?

## WITH RECURSIVE f(e) peel until non-array; single-value lookups return null (caller keeps raw column)
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/providers/pg-record-query-dialect.ts:flattenLookupCteValue` (:330-349) + shared `buildDistinctFlattenedJsonArray` (:27-39).
**Signature:** `flattenLookupCteValue(cteName: string, fieldId: string, isMultiple: boolean, _dbFieldType): string | null`.
**Data Shape:** input column `"CTE_x"."lookup_<id>"`; output a scalar subquery of jsonb_agg over leaf elements; null returned for isMultiple=false.

### Decisive source
```sql
(WITH RECURSIVE f(e) AS (
  SELECT to_jsonb("cte"."lookup_fld1")
  UNION ALL
  SELECT jsonb_array_elements(f.e) FROM f WHERE jsonb_typeof(f.e) = 'array'
)
SELECT jsonb_agg(e) FILTER (WHERE jsonb_typeof(e) <> 'array') FROM f)
```

**Flow:** multi-value lookup reading another multi-value lookup → CTE value may nest arrays → recursive CTE peels array levels via jsonb_array_elements until elements are scalars/objects → aggregate leaves (FILTER drops residual arrays) → used as the SELECT expression for the outer lookup.
**Invariant:** recursion terminates because each iteration only expands elements whose typeof = 'array' and jsonb has no cycles; the FILTER inside the final agg (not a WHERE on the recursive member) keeps null/object leaves. Single-value lookups must NOT be wrapped — the null-return contract lets the caller fall back to the plain CTE column reference (`??"lookup_<id>"`).
**Probe:** upstream direct spec `pg-record-query-dialect.spec.ts:6-30` pins all three polarities (null for single-value; to_jsonb normalization for json-stored AND scalar payloads).

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"flattenLookupCteValue","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the recursive-peel shape for nested lookups. Adapt aliasing. Omit the distinct-sort variant if you don't need set semantics.
