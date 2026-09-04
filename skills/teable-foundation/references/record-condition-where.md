<!-- capsule-v2 -->
# Record-condition WHERE compiler — how do typed per-field conditions become Postgres predicates that treat NULL/jsonb/multiplicity correctly?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What SQL shape does each operator family produce, and where would a naive port emit wrong rows?

## three-valued emptiness + jsonb containment lists + date-range modes + operand polymorphism
**Path/Symbol:** `packages/v2/adapter-repository-postgres/src/repositories/visitors/TableRecordConditionWhereVisitor.ts` — `resolveDateRange` (179–348), `buildIsEmptyCondition` (350–374), `buildIsNotEmptyCondition` (376–402), `buildListCondition` (547–582), `buildDateComparisonCondition` (499–529), `buildIsNotCondition` (424–444), operand resolution (107–130); test `TableRecordConditionWhereVisitor.spec.ts` snapshot matrix :503+, record-id list :538–552, alias date-comparison :554+.
**Signature:** `new TableRecordConditionWhereVisitor({ tableAlias? })`; visits yield `RecordConditionWhere = ReturnType<typeof sql>` raw fragments composed via and/or/not.

### Decisive source
```ts
// emptiness is THREE-valued by cell type:
isMultiple  → `(col is null) or (jsonb_array_length(to_jsonb(col)) = 0)`
fieldIsJson → `(col is null) or (to_jsonb(col) = '{}'::jsonb)`
string      → `(col is null) or (col = '')`
other       → `col is null`                       // number/date/bool have no second empty state
// list ops on multi-value cells (values stringified for ?|):
any   → to_jsonb(col) ?| array[...text]
none  → not (... ?| ...)
all   → to_jsonb(col) ?& array[...text]
exact → (col @> arr) and (col <@ arr)               // bidirectional containment = set equality
notExact → not ((…) and (…))
// single-value cells fall back to plain IN / NOT IN
// isNot keeps NULLs visible: `(col not between a and b or col is null)` — asymmetric with `is`!
// date comparison picks ONE boundary from the range: '>'/'<=' take range.end; '>='/'<' take range.start
// operands are polymorphic: literal → param binding, field-reference → sql.ref(column) (column-to-column compare)
```

**Flow:** each visit method maps to one of nine private appliers → builders resolve column (with optional tableAlias prefixing for lateral subqueries, remapping missing-db-field-name errors to `invariant.missing_db_field_name`) → date values expand to `[start,end]` ISO strings through the 27-mode taxonomy (fixed days, offset-days, exact date/datetime/format-unit, relative week/month/year periods with Monday week-start injected, past/next N days) whose unit granularity derives from the FIELD's date formatting preset (Y→year, YM/M→month, else day) → conditions accumulate through addCond so `visitor.where()` replays them combined.
**Invariant:** NULL handling is deliberately asymmetric: `is` excludes nulls but `isNot` ORs `is null` back in — dropping that clause makes "not equal X" swallow NULL rows. List operators stringify values because jsonb `?|/?&` operate on text keys; using typed arrays breaks containment semantics. Date ranges are computed in the CONDITION'S timezone then compared against stored UTC instants — computing in server-local time shifts every boundary.
**Probe:** `TableRecordConditionWhereVisitor.spec.ts` :503 `test.each(cases)` compiles the whole operator×type matrix into SQL snapshots; :538 asserts parameterized `__id in (...)`; :554 pins alias-prefixed `"t"."col_due_date" < "t"."col_due_date"` for field-reference comparison.
**Coverage:** fully indexed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "resolveDateRange buildListCondition buildIsEmptyCondition TableRecordConditionWhereVisitor", limit: 10 });
```

## Verdict
Adopt the emptiness ladder, the jsonb list-operator set, and the null-preserving negation verbatim — these encode Postgres three-valued logic. Adapt the 27-mode date taxonomy to host UI vocabulary but keep format-preset-derived granularity. Omit nothing else; every branch corresponds to a distinct cell-type × operator combination.
