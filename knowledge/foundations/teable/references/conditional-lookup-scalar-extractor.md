<!-- capsule-v2 -->
# conditional-lookup-scalar-extractor — How does a scalar function receive ONE value from a multi-value lookup argument?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What SQL extracts the first meaningful scalar from a jsonb array when a function demands a single value?

## normalizeMultiValueExprToJson → first non-null element by ordinality → title/name/scalar ladder → datetime reformat
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/sql-conversion.visitor.ts:buildPgSingleValueExtractor` (:1264-1291) + `normalizeMultiValueExprToJson` (:1315-1334) + `formatScalarDatetimeIfNeeded` (:1293-1313).
**Signature:** `reduceMultiFieldReferenceParam(exprCtx, paramSql)` dispatches here whenever the param is multi-value AND the function doesn't accept multi.
**Data Shape:** pg_typeof-driven coercion CASE (json/json/text→array-wrap fallback/other→to_jsonb) then array-normalization CASE; element pick = first by WITH ORDINALITY order excluding jsonb null.

### Decisive source
```sql
(SELECT elem FROM jsonb_array_elements(<normalizedJson>) WITH ORDINALITY AS t(elem, ord)
 WHERE jsonb_typeof(elem) <> 'null' ORDER BY ord LIMIT 1)
...
CASE WHEN <scalarJson> IS NULL THEN NULL
     WHEN jsonb_typeof(...) = 'object' THEN COALESCE(x->>'title', x->>'name', x::text)
     WHEN jsonb_typeof(...) = 'array'  THEN NULL
     ELSE <datetime-formatted scalar #>> '{}'>
END
```

**Flow:** function param classified multi-value (isMultiValueExpr over AST + emitted SQL) → not in MULTI_VALUE_AGGREGATED_FUNCTIONS and interceptor won't handle → reduce to single scalar via extractor → datetime-typed fields get dialect.formatDate applied to the extracted text (skipped entirely inside generated columns where immutability forbids it).
**Invariant:** object elements resolve through the title→name→text preference chain (links carry titles; plain objects fall back to name); array-of-array yields NULL rather than recursing. Generated-column contexts must NOT embed formatDate — that's the isGeneratedColumn early return.
**Probe:** static byte-exact: `grep -n 'ORDER BY ord' sql-conversion.visitor.ts | head -3`; upstream spec pins the sibling IF-side extraction (`select-query.postgres.spec.ts` IF json-numeric case).

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"buildPgSingleValueExtractor","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the extractor ladder incl. the generated-column exemption. Adapt preference keys. Omit nothing.
