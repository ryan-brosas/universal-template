<!-- capsule-v2 -->
# aggregate-group-choice-order — How are group-by result rows ordered by select-field CHOICE order rather than alphabetically?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What SQL orders grouped aggregates by SingleSelect/MultipleSelect option sequence, including jsonb arrays?

## ARRAY_POSITION over choice names; multi-select reads first element via jsonb_path_query_first; doubled bindings
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts:orderAggregateByGroup` (:334-400) + `normalizeOrderableTextExpression` (:402-422).
**Signature:** `private orderAggregateByGroup(qb, field: FieldCore, direction: 'ASC'|'DESC', selectionMap)`.
**Data Shape:** nullOrdering = DESC→`NULLS LAST`, else `NULLS FIRST`; array literal built with one `?` placeholder per choice; MultipleSelect binds the choice list TWICE.

### Decisive source
```ts
if (field.type === FieldType.MultipleSelect) {
  const firstIndexExpr = `CASE
    WHEN ${sel} IS NULL THEN NULL
    WHEN jsonb_typeof(${sel}::jsonb) = 'array'
      THEN ARRAY_POSITION(${arrayLiteral}, jsonb_path_query_first(${sel}::jsonb, '$[0]') #>> '{}')
    ELSE ARRAY_POSITION(${arrayLiteral}, ${sel}::text)
  END`;
  // arrayLiteral appears twice in firstIndexExpr, so duplicate bindings
  qb.orderByRaw(`${firstIndexExpr} ${direction} ${nullOrdering}`, [...choiceNames, ...choiceNames]);
  qb.orderByRaw(`${orderableSelection}::jsonb::text ${direction} ${nullOrdering}`);
  return;
}
```
User/link fields order by extracted title (`(expr)::jsonb ->> 'title'`, or `jsonb_path_query_array(... '$[*].title')::text` when multi).

**Flow:** resolve the group field's selection expression (string or knex raw .toQuery()) → select-family fields get the ARRAY_POSITION CASE (single: direct text normalize; multi: first-element probe + a SECOND orderBy on the full jsonb text for stability) → user/link family title ordering → default quoted-alias ordering.
**Invariant:** the binding count must match the number of times `arrayLiteral` is spliced — the in-source comment calls it out; missing the duplication throws a bind-count error only at execution. The secondary jsonb-text sort makes rows within equal first-elements deterministic.
**Probe:** static byte-exact: `grep -n 'duplicate bindings' apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts` → :386; upstream spec `record-query-builder-group-quoting.spec.ts:173+` pins quoting of these very ORDER BY expressions for projected and non-projected group fields (bare identifiers must stay quoted or PG folds case → 42703).

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"orderAggregateByGroup","limit":3,"detail":"ids"}'
```

## Verdict
Adopt choice-position ordering + double-binding rule. Adapt choice storage. Omit nothing.
