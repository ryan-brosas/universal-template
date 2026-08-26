<!-- capsule-v2 -->
# PG per-level lookup limits — how do sort+limit configs survive compilation into a formula's JOIN spine?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** Where do OUTER (first-hop) and INNER (nested) top-N restrictions get applied, and why are they PG-only?

## outer pk-IN + inner correlated limits
**Path/Symbol:** outer: `lookup-or-ltar-builder.ts` :284-311 (`applyLookupPkInLimit` call :302); inner BT: :390-407 (`applyNestedLookupLevelLimit` :395); inner HM: :442-459 (call :447) — all gated `baseModelSqlv2.isPg`.
**Signature:** `applyLookupPkInLimit({qb, alias, refBaseModel, sorts, limitVal, takeLast})` mutates the still-plain selectQb; `applyNestedLookupLevelLimit({qb, nestedAlias, nestedRefBaseModel, corrColName, prevAlias, prevCorrColName, sorts, limitVal, takeLast})`.
**Data Shape:** Config from `loadLookupSortAndLimit(context, column)` → `{hasConfig, sorts, limitVal>0, takeLast}`; applied only when hasConfig && limitVal > 0.

### Decisive source
```ts
// :284-289 — why OUTER runs before the loop turns qb into a function:
// Per-lookup Limit — OUTER level (PG): restrict the first-level relation
// rows a formula sees to the configured top-N BEFORE any nested joins,
// correlated to the root row. Applies to single-level lookups and the
// outer level of nested ones (the pk-IN survives the nested joins below).
// selectQb is still a plain builder here (it only becomes a function in
// the terminal switch after the loop).
if (column.uidt === UITypes.Lookup && baseModelSqlv2.isPg &&
    typeof (selectQb as any)?.clone === 'function') { ... }
```

**Flow:** outer level — if root column is a Lookup with config, rank the FIRST relation's rows per parent and pin them via a pk-IN subquery so every deeper join only sees the visible top-N → inner levels — each BT/HM nesting applies ITS OWN column's config as a correlated restriction between prevAlias and nestedAlias → MM nested levels get NO inner limit (matches the display builder's contract).
**Invariant:** (1) The `typeof clone === 'function'` guard is a structural duck-check that selectQb is still a QueryBuilder — after the terminal switch it's a function and calling limit on it would crash; ordering is load-bearing. (2) All three applications are PG-only because the ranking primitive (ROW_NUMBER window / pk-IN ladder) lives in lookupSortLimit's PG implementation; porting to MySQL needs its own window-function story or the three consumers (display/filter/formula) diverge. (3) Inner limits correlate via BOTH prevAlias.prevCorrColName AND nestedAlias.corrColName — dropping either side un-bounds the top-N.
**Probe:** No unit tests upstream. Deterministic probe: search_graph resolves `applyLookupPkInLimit`, `applyNestedLookupLevelLimit`, `loadLookupSortAndLimit` under `packages/nocodb/src/db/lookupSortLimit.ts`; grep :293 duck-guard line.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "lookupSortLimit", limit: 10 });
// the shared primitive trio consumed by display, filter, AND formula planes
```

## Verdict
Adopt the outer-before-loop/inner-per-level placement discipline and the three-consumer parity requirement; adapt the window SQL per engine; omit non-PG silently (upstream does). Caveat: no direct tests at pin.
