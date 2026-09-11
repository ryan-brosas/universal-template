<!-- capsule-v2 -->
# multi-value-lookup-jsonagg — How are multi-value lookup cells aggregated deterministically inside a link CTE?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What exact json_agg shape (ORDER BY, FILTER, sanitization) must a porter reproduce?

## json_agg(sanitized ORDER BY stable-ladder) FILTER (WHERE EXISTS-sub AND NOT NULL)
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/field-cte-visitor.ts:visitLookupField` (:418-532, aggregation tail :508-531); order ladder :459-487.
**Signature:** `private visitLookupField(field: FieldCore): IFieldSelectName`.
**Data Shape:** single-value contexts (`!isMultipleCellValue || isSingleValueRelationshipContext`) skip aggregation entirely; per-field filter compiles to an `EXISTS` subquery via `buildForeignFilterSubquery`.

### Decisive source
```ts
const sanitizedExpression = this.normalizeJsonAggregateExpression(expression);
if (orderByClause) {
  return `json_agg(${sanitizedExpression} ORDER BY ${orderByClause}) FILTER (WHERE (EXISTS ${sub}) AND ${sanitizedExpression} IS NOT NULL)`;
}
return `json_agg(${sanitizedExpression}) FILTER (WHERE (EXISTS ${sub}) AND ${sanitizedExpression} IS NOT NULL)`;
// no-filter fast path keeps the same ORDER BY ladder:
return `json_agg(${sanitizedExpression} ORDER BY ${orderByClause}) FILTER (WHERE ${sanitizedExpression} IS NOT NULL)`;
```
Order ladder (junction links): `` j."<order>" IS NULL DESC, j."<order>" ASC, j."__id" ASC `` — NULLS-FIRST semantics so unordered rows sort before ordered ones; without an order column the tiebreak degrades to junction `__id ASC`; non-junction uses the foreign alias.

**Flow:** resolve target physical expression (typed NULL when errored) → optional ISO-UTC normalization for datetime targets (see lookup-date-iso-normalize) → derive deterministic ORDER BY from the LINK field's config → wrap in sanitized json_agg with FILTER.
**Invariant:** every multi-value aggregate carries BOTH a total-order tiebreak and a FILTER clause — omitting either yields nondeterministic arrays or `[null]` entries. The EXISTS form applies the field's OWN filter per column (global filter application was deliberately removed — see the "Removed global application" comments ×3).
**Probe:** static byte-exact: `grep -c 'FILTER (WHERE' field-cte-visitor.ts` → 4; `grep -n "to_char(\${expression} AT TIME ZONE 'UTC'" field-cte-visitor.ts` → :480.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"visitLookupField","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the aggregate shape verbatim (modulo dialect). Adapt the order-column naming. Omit nothing — the NULLS DESC + __id tiebreak is the determinism contract.
