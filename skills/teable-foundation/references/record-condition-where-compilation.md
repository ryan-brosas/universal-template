<!-- capsule-v2 -->
# RecordConditionWhereCompilation — typed condition specs → raw Postgres predicates

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does the 2,400-line condition visitor compile every per-field filter operator into a raw Postgres predicate, and what NULL/array/jsonb traps must a porter preserve?

## Condition-where visitor
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/visitors/TableRecordConditionWhereVisitor.ts` (whole file, 1-2400) + `record/repository/buildRecordWhereClause.ts` (19-39).
**Signature:** `new TableRecordConditionWhereVisitor({tableAlias?, hostTableAlias?})`; `spec.accept(visitor)` → `visitor.where()` → `RecordConditionWhere` (a `sql` RawBuilder); `buildRecordWhereClause(spec, options)` returns `null` on empty-where (so callers skip the WHERE).
**Data Shape:** `RecordConditionWhere = ReturnType<typeof sql>`. Operators compile via module-level builders (`buildIsCondition`, `buildIsNotCondition`, `buildContainsCondition`, `buildNumericComparisonCondition`, `buildDateComparisonCondition`, `buildIsWithinCondition`, `buildListCondition`) plus the class's `visit*` methods and `apply*` wrappers. Field references (operand kind `field`) vs literals are resolved by `resolvePrimitiveOperand`.

### Decisive source
```ts
// NULL-preserving negation — the classic trap. v1 semantics: NULL rows PASS "not in"/"does not contain".
// isNot list (non-multiple): COALESCE(col,'') not in (...)   // NULL → '' → passes NOT IN
const isNegative = kind === 'none' || kind === 'notExact';
return ok(isNegative ? sql`coalesce(${columnRef}, '') not in (${list})` : sql`${columnRef} in (${list})`);
// doesNotContain: COALESCE(col,'') not ilike ...  // NULL rows pass
const condition = isNegative
  ? sql`coalesce(${columnRef}, '') not ilike ${pattern} escape '\\'`
  : sql`${columnRef} ilike ${pattern} escape '\\'`;
```

**Flow:** `visitXIs/IsNot/Contains/...` → `apply*` wrapper → `addConditionResult` (runs the builder then `addCond` to accumulate) → builder resolves column (alias-prefixed), resolves the operand (literal or field-ref), then emits per-type SQL. Array-like outputs (multiple/lookup/conditionalLookup) normalize via `normalizeToJsonArray` and use `jsonb_array_elements_text` + EXISTS. User/link fields extract `$.id` via `jsonb_path_query_array` and compare id arrays (`@>`/`jsonb_exists_any`). Date values resolve to a `{start,end}` range (see date-range capsule) and compile to `BETWEEN`/`EXISTS`. Field-vs-field references route through `classifyFieldReferenceComparison` (userOrLinkIds / linkTitle / date / json / generic / incompatible).

**Invariant:** NULL handling is asymmetric and deliberate — positive operators exclude NULL rows, but negative operators (`not in`, `doesNotContain`, `isNoneOf`, `notExact`) use `COALESCE(col,'')` so NULL rows PASS (v1 parity). Checkbox `is false` matches `false OR NULL` (unchecked is stored NULL, not false). `incompatible` field-reference comparisons compile to `1=0` (is) / `1=1` (isNot) — never equal, so isNot is always true.

**Probe:** `record/visitors/TableRecordConditionWhereVisitor.spec.ts` — `'NULL handling'` describe (:385) with `isNot` (:401), `doesNotContain` (:432), `isNoneOf` (:463), `checkbox is` (:485), `date field reference comparisons` (:527), `user field reference operators` (:826).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildIsNotCondition COALESCE not ilike jsonb_array_elements_text", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the operator→builder→predicate compilation and the NULL-passing negative-operator semantics (the single most likely porting bug). Adapt the `tableAlias`/`hostTableAlias` cross-table reference routing (conditional-lookup comparisons). Omit the 27-mode date taxonomy (dedicated capsule). Probes pinned to the real spec suite.
