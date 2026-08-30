<!-- capsule-v2 -->
# Choice-order group sorting — ARRAY_POSITION CASE ladders with doubled bindings

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How do grouped aggregates sort by select-field CHOICE ORDER (not alphabetical) and by user/link display title?

## orderAggregateByGroup per-type expression ladder
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts:orderAggregateByGroup` (:333–400) + `normalizeOrderableTextExpression` (:402–421); called from `createRecordAggregateBuilder` :297–303.
**Signature:** `orderAggregateByGroup(qb, field, 'ASC'|'DESC', selectionMap)`; NULLS FIRST on ASC, NULLS LAST on DESC (:340).
**Data Shape:** SingleSelect cells = scalar text; MultipleSelect = jsonb array; user/link = jsonb `{title}` or array of them.

### Decisive source
```ts
if (field.type === FieldType.MultipleSelect) {
  const firstIndexExpr = `CASE
    WHEN ${orderableSelection} IS NULL THEN NULL
    WHEN jsonb_typeof(${orderableSelection}::jsonb) = 'array'
      THEN ARRAY_POSITION(${arrayLiteral}, jsonb_path_query_first(${orderableSelection}::jsonb, '$[0]') #>> '{}')
    ELSE ARRAY_POSITION(${arrayLiteral}, ${orderableSelection}::text)
  END`;
  // arrayLiteral appears twice in firstIndexExpr, so duplicate bindings
  qb.orderByRaw(`${firstIndexExpr} ${direction} ${nullOrdering}`, [...choiceNames, ...choiceNames]);
  qb.orderByRaw(`${orderableSelection}::jsonb::text ${direction} ${nullOrdering}`);
  return;
}
```

**Flow:** Select fields sort rows by the position of their FIRST choice in the field's declared choice list (`ARRAY_POSITION` over an `ARRAY[?,?]...` literal); multi-select adds a secondary raw-jsonb-text ordering for intra-choice stability. User/link fields sort by `->> 'title'` (single) or `jsonb_path_query_array(...,'$[*].title')::text` (multi). Everything else orders by the quoted alias. Jsonb-typed text columns route through a CASE that unwraps string/number/bool/array-first-element before comparison.
**Invariant:** The comment at :363 is the trap — `arrayLiteral` is INTERPOLATED TWICE into the CASE, so knex placeholder bindings must be `[...choiceNames, ...choiceNames]`; passing them once silently mis-binds every choice after the first. The fallback second orderBy for multi-select exists because two rows sharing a first choice need ANY deterministic tiebreak. Porters who alphabetize choices break the grid's visible order contract — the grid groups render in choice-declaration order.
**Probe:** `grep -cF 'ARRAY_POSITION' apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts` → 3; `grep -cF '\$[*].title' apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "orderAggregateByGroup ARRAY_POSITION choice", limit: 10 });
```

## Verdict
Adopt declaration-order sorting via positional array lookups; adapt to your DB's array-index function; never drop the duplicate-binding rule when templating.
