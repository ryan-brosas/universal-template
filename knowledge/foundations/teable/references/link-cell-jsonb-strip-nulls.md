<!-- capsule-v2 -->
# link-cell-jsonb-strip-nulls — What JSON shape does a link CTE cell carry and how are null titles removed?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How is the `{id, title}` object built for link cells (single and multi)?

## jsonb_strip_nulls(jsonb_build_object('id', …, 'title', …))::jsonb
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/providers/pg-record-query-dialect.ts:buildLinkJsonObject` (:648-651); consumed in `field-cte-visitor.ts:visitLinkField` (:555-645).
**Signature:** `buildLinkJsonObject(recordIdRef: string, formattedSelectionExpression: string, _rawSelectionExpression: string): string`.
**Data Shape:** multi-value → `json_agg(<object> ORDER BY <ladder>) FILTER (WHERE id IS NOT NULL [AND EXISTS sub])`; single-value → `CASE WHEN <cond> THEN <object> ELSE NULL END`.

### Decisive source
```ts
return `jsonb_strip_nulls(jsonb_build_object('id', ${recordIdRef}, 'title', ${formattedSelectionExpression}))::jsonb`;
...
// visitor side — multi-value tail:
const sanitizedExpression = this.normalizeJsonAggregateExpression(conditionalJsonObject);
return `json_agg(${sanitizedExpression} ORDER BY ${orderByClause}) FILTER (WHERE ${appliedFilter})`;
```

**Flow:** display expression produced by FieldFormattingVisitor over the foreign primary field (alias rewrites via `replaceAll` when self-joined) → object built with id + title → strip_nulls removes the `"title"` KEY whenever it is SQL NULL (so `{id}` objects instead of `{id, title:null}`) → aggregate or CASE-wrap.
**Invariant:** jsonb_strip_nulls is what makes "link without title" and "title literally null" indistinguishable-by-design; consumers must treat missing key as empty title. The FILTER keeps rows whose foreign record vanished out of the array entirely rather than emitting null elements.
**Probe:** upstream direct spec `providers/pg-record-query-dialect.spec.ts` (`describe('PgRecordQueryDialect#linkExtractTitles')`) pins sibling title extraction without pg_typeof guards; static probe `grep -n 'jsonb_strip_nulls' providers/pg-record-query-dialect.ts` → :653.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"buildLinkJsonObject","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the object shape + strip-nulls semantics. Adapt formatting hooks. Omit nothing.
