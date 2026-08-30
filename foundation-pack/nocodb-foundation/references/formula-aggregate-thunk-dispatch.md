<!-- capsule-v2 -->
# formula identifier aggregate thunk — how does a bare `{LookupField}` inside ADD()/CONCAT() become MIN(col)/SUM(col), and why does databricks get string surgery?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How does the Identifier branch of `fn()` resolve a function-returning builder, and what is the databricks trailing-`)` rewrite actually for?

## Identifier resolution + aggregate-thunk call + databricks LIMIT-1 surgery
**Path/Symbol:** `packages/nocodb/src/db/formulav2/formulaQueryBuilderv2.ts:_formulaQueryBuilder.fn` (:436–456); producer contract `packages/nocodb/src/db/formulav2/lookup-or-ltar-builder.ts` isArray fork (:549–558, :701–710, :853–862); consumer table `packages/nocodb/src/db/formulav2/formula-query-builder.helpers.ts:getAggregateFn` (:141–185).
**Signature:** `(pt: IdentifierNode) => { builder: Knex.Raw }`; thunk shape `selectQb = (fn: string) => knex.raw(getAggregateFn(fn)({qb, knex, cn})).wrap('(',')')`.
**Data Shape:** `aliasToColumn[pt.name]()` resolves the column's builder factory; the factory's return is either `{builder}` (plain) or a raw whose builder IS a function awaiting the parent formula fn name. `getAggregateFn(parentFn)` maps that name to an aggregate applicator over the captured subquery `cn`.

### Decisive source
```ts
// formulaQueryBuilderv2.ts :436–444 — a FUNCTION builder means "call me with the parent fn name"
} else if (pt.type === 'Identifier') {
  const { builder } =
    (await aliasToColumn?.[pt.name]?.({ tableAlias, parentColumns: params.parentColumns })) || {};
  if (typeof builder === 'function') {
    return { builder: knex.raw(`??`, builder(pt.fnName)) };
  }

// :446–454 — databricks cannot bind a derived-table alias without LIMIT; strip ONE trailing paren, append
  if (
    knex.clientType() === 'databricks' &&
    builder.toQuery().endsWith(')')
  ) {
    // limit 1 for subquery
    return {
      builder: knex.raw(`${builder.toQuery().replace(/\)$/, '')} LIMIT 1)`),
    };
  }
```
```ts
// lookup-or-ltar-builder.ts :549–556 — who PRODUCES thunks: every isArray (multi-row) terminal
if (isArray) {
  const qb = selectQb;                    // capture BEFORE reassignment — closure needs the pre-fork qb
  selectQb = (fn) =>
    knex.raw(
      getAggregateFn(fn)({ qb, knex, cn: knex.raw(builder).wrap('(', ')') }),
    ).wrap('(', ')');
}
```

**Flow:** when a formula references a multi-row Lookup/LTAR column directly (`ADD(lookupField)`, `CONCAT(lookupField)`), the lookup builder has ALREADY converted `selectQb` into a function expecting one argument. The parent CallExpression pass stamped `arg.fnName = callee.name.toUpperCase(); arg.argsCount` onto every argument BEFORE recursion (:377–383), so at Identifier time `pt.fnName` carries the enclosing function name; `builder(pt.fnName)` executes `getAggregateFn(name)` and returns e.g. `MIN((subquery))`, `SUM(...)`. `getAggregateFn`'s dispatch table holds the porting surprises: **AVG deliberately routes to `.sum()`** (:154–155 — average over linked rows is computed as sum here; upstream carries a commented-out true-average draft under `// todo:`), **FIRST is `.select(cn).limit(1)`** relying on the subquery's existing `ORDER BY nc_order` (:172–175 — ordering lives in the subquery, not the aggregate), ARRAY_AGG/NO_AGG select raws, CONCAT/default concat via `qb.clear('select').concat(cn, (qb as any)?._ncLinkOrderRef)` where `_ncLinkOrderRef` is an opt-in PG-only ordered-mm stash that is ABSENT in every other case (:177–183), and every arm starts with `qb.clear('select')` because the captured qb still holds its projection.
**Invariant:** (1) The `typeof builder === 'function'` duck-test is THE protocol distinguishing "column expression" from "aggregate waiting for its parent function" — wrapping it in a class/interface or checking a marker property breaks the lookup-builder contract unless both sides change together. (2) `arg.fnName` stamping must happen on arguments BEFORE child recursion; a thunk resolving with `undefined` silently falls to the CONCAT/default arm. (3) The databricks branch fires ONLY when the rendered SQL ends in `)` — it strips exactly ONE closing paren and appends `LIMIT 1)`; doing this via knex `.limit()` on a raw is impossible, so the string surgery is load-bearing, and the `??`-bound result keeps the subquery as an identifier-safe operand. (4) Every `getAggregateFn` arm must `clear('select')` first or the captured subquery double-projects and the outer wrap emits invalid SQL.
**Probe:** `grep -n "builder(pt.fnName)" packages/nocodb/src/db/formulav2/formulaQueryBuilderv2.ts` → exactly :443; `grep -c "LIMIT 1)" packages/nocodb/src/db/formulav2/formulaQueryBuilderv2.ts` → 1; `grep -c "clear('select')" packages/nocodb/src/db/formulav2/formula-query-builder.helpers.ts` → 9. Runner BLOCKED (no upstream unit tests cover db/formulav2) → line-anchored deterministic checks.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "getAggregateFn isArray selectQb _ncLinkOrderRef", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the function-builder thunk protocol with parent-fnName stamping and the clear('select') discipline; adapt AVG→SUM and FIRST→limit(1)-over-display-order only if host semantics keep linked-row averaging as sum; omit the databricks string surgery outside databricks targets (keep it byte-for-byte if targeting databricks).
