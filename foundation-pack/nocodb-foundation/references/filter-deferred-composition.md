<!-- capsule-v2 -->
# conditionV2 clause composition — why does every branch return a deferred {clause, rootApply} pair instead of mutating the query builder?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** What is the exact contract of a `FilterOperationResult`, and when must rootApply fire vs. the nested clause?

## Deferred FilterOperationResult
**Path/Symbol:** `packages/nocodb/src/db/conditionV2.ts:parseConditionV2` (:145-886), entry `conditionV2` (:32-58).
**Signature:** `parseConditionV2(baseModelSqlv2, _filter: Filter|FilterType|FilterType[] , aliasCount = {count:0}, alias?, customWhereClause?, throwErrorIfInvalid?): Promise<FilterOperationResult>`; entry applies `filterOperationResult.clause(qb); filterOperationResult.rootApply?.(qb)` in that order.
**Data Shape:** `aliasCount` is a SHARED mutable `{count}` threaded through recursion (cross-table dynamic filters mint `__nc_df${count++}` aliases). `customWhereClause` swaps roles: `filter.value` becomes the FIELD and the clause becomes the VALUE (used by formula/rollup compiled-expression paths). Disabled filters (`enabled === false || enabled === 0`) and null array entries are dropped BEFORE recursion (`supportToggle` from `Filter.supportToggle(context)`).

### Decisive source
```ts
// :184-199 — array form wraps children in ONE group; logical_op comes from
// the PARENT ARRAY entries, not from any single child
return {
  rootApply: (qbP) => { for (const qb1 of qbs) qb1?.rootApply?.(qbP); },
  clause: (qbP) => {
    qbP.where((qb) => {
      for (const [i, qb1] of Object.entries(qbs)) {
        if (qb1) qb[getLogicalOpMethod(enabledFilters[i])](qb1.clause);
      }
    });
  },
};
// :200-236 — is_group: same shape but children keep their OWN logical ops;
// disabled groups cascade-skip to {clause: noop, rootApply: noop}
// :56-57 — entry point ordering:
filterOperationResult.clause(qb);
filterOperationResult.rootApply?.(qb);
```

**Flow:** verifyFilters (FieldHandler) → parse → three shapes: flat array (implicit AND-group, per-child op honored) / `is_group` (children re-parse with own ops) / leaf leaf-filter (groupby rewrite → dynamic filter hook → FieldHandler early-route list → generic switch). Every path returns a closure pair; NOTHING touches the real qb until the caller invokes them.
**Invariant:** (1) Clause closures must be idempotent-safe under single application — they capture `_field/_val` computed at PARSE time (including `handleCurrentUserFilter` substitution and `getColumnName` re-resolution), so late query changes don't leak into bindings. (2) A skipped filter is an EMPTY no-op clause, never `undefined`, so parent composition `qb[op](qb1.clause)` stays type-stable. (3) `rootApply` exists for clauses that must attach at the ROOT builder (e.g. CTE/join-dependent pieces) and fires AFTER clause.
**Probe:** No unit tests upstream. Deterministic probe: build `[{a eq x},{b like y}]` → renders `(a = ? AND b like ?)`; disabled child drops only its term; group with `not` renders `NOT (...)`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "parseConditionV2", limit: 5 });
// nocodb.packages.nocodb.src.db.conditionV2.parseConditionV2 Function conditionV2.ts 145-886
```

## Verdict
Adopt the deferred two-slot result and empty-clause-not-undefined discipline verbatim — it is what lets filters compose inside lookups, EXISTS subqueries, and count queries. Adapt the FieldHandler early-route uidt list (product surface). Caveat: no direct tests; graph ranges verified live.
