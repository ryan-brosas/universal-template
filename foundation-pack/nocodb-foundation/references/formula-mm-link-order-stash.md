<!-- capsule-v2 -->
# MM link-order default sort — how does junction per-link Order reach the aggregate when the lookup has no config?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How is the manual drag-order of an MM link honored inside a formula lookup, and what happens when a user sort config exists?

## _ncLinkOrderRef stash
**Path/Symbol:** `packages/nocodb/src/db/formulav2/lookup-or-ltar-builder.ts` :237-253.
**Signature:** `(selectQb as any)._ncLinkOrderRef = knex.raw('??', [`${assocAlias}.${linkOrderCol.column_name}`])` — a non-knex property smuggled on the QueryBuilder for the aggregate stage to read.
**Data Shape:** Set ONLY when `baseModelSqlv2.isPg`, relation is MM, and `loadLookupSortAndLimit(context, column).hasConfig === false` (i.e. NO user sort/limit config); value = raw ref to the junction's Order column under assocAlias.

### Decisive source
```ts
// :237-243 — the contract comment:
// Per-link ordering (PG only): stash the junction Order column ref
// (current side) on the row query so the aggregate (getAggregateFn →
// concat) can ORDER BY it. Absent for non-PG / v1 / external links.
// Only as the DEFAULT order — if this lookup has its own sort/limit
// config, that ordering wins, so skip the link order to avoid
// overriding it.
if (baseModelSqlv2.isPg) {
  const lookupCfg = await loadLookupSortAndLimit(context, column);
  const linkOrderCol = lookupCfg.hasConfig
    ? null                                   // user ordering wins
    : await relation.getMMChildOrderColumn(context);
```

**Flow:** first-hop MM arm → probe for a user sort/limit config → if none and PG, resolve the junction's child-side Order column → stash its alias-qualified ref on selectQb as `_ncLinkOrderRef` → the terminal aggregate (`getAggregateFn(fn)({qb, knex, cn})`, helpers file) reads that property and appends ORDER BY so CONCAT aggregates list links in drag order.
**Invariant:** (1) Config-wins rule: stashing when hasConfig would produce two competing ORDER BY sources — the explicit skip IS the precedence mechanism. (2) The side-channel property survives `.clone()` but NOT `toQuery()` materialization; it must be read while qb is still a builder. (3) Non-PG/v1/external links get no default order by design — silent absence, not an error.
**Probe:** No unit tests upstream. Deterministic probe: grep `_ncLinkOrderRef` in this file (:249 sole writer) + search_graph `getMMChildOrderColumn` resolves line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "getMMChildOrderColumn", limit: 5 });
```

## Verdict
Adopt the stash-on-builder side-channel pattern for passing compile-stage hints to aggregate stages; adapt to typed fields if your builder allows; omit for non-window-function engines (upstream does). Caveat: no direct tests at pin.
