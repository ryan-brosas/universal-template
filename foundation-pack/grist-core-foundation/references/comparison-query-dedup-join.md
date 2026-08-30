<!-- capsule-v2 -->
# Deduplicated comparison join — how do you diff two homogeneous SQLite tables row-by-row without the join exploding on duplicate keys?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you build a SQL diff (added/updated rows) between an import source table and a destination table when destination join columns may hold duplicates?

## Pre-deduplicate the right table via `MIN(id) GROUP BY` before joining, then `IS NOT`-filter to true differences
**Path/Symbol:** `app/server/lib/ExpandedQuery.ts:buildComparisonQuery` (:176–263); helper `combineExpr` (:265–267); consumer `app/server/lib/ActiveDocImport.ts:598`.
**Signature:** `function buildComparisonQuery(leftTableId: string, rightTableId: string, selectColumns: Map<string, string[]>, joinColumns: Map<string, string>): ExpandedQuery`.
**Data Shape:** `selectColumns`: left colId → one-or-more matching right colIds; `joinColumns`: right colId → left colId. Output columns are aliased `"tableId.colId"` so both tables' values coexist in one result row.

### Decisive source
```ts
// Performance can suffer when large (right) tables have many duplicates for their join columns.
// ...we de-duplicate the right table before joining, returning the first row id
// we find for a given group of join column values.
const dedupedRightTableQuery =
  `SELECT MIN(id) AS id, ${[...joinColumns.keys()].map(v => quoteIdent(v)).join(", ")} ` +
  `FROM ${quoteIdent(rightTableId)} ` +
  `GROUP BY ${[...joinColumns.keys()].map(v => quoteIdent(v)).join(", ")}`;
const dedupedRightTableAlias = quoteIdent("deduped_" + rightTableId);
// Join left → deduped right, then deduped right → original right to recover all columns.
joins.push(`LEFT JOIN (${dedupedRightTableQuery}) AS ${dedupedRightTableAlias} ON ${joinConditions.join(" AND ")}`);
joins.push(`LEFT JOIN ${quoteIdent(rightTableId)} ON ${dedupedRightTableAlias}.id = ${quoteIdent(rightTableId)}.id`);
...
whereConditions.push(`${leftColumnAlias} IS NOT ${rightColumnAlias}`);
```

**Flow:** select both `id`s plus every mapped column under dotted aliases → build a subquery that collapses the right table to one representative row per join-key group (`MIN(id)` = first-inserted wins) → LEFT JOIN left table to the deduped alias on all join conditions, then LEFT JOIN that alias back to the full right table by id → WHERE keeps only unmatched-left rows and matched rows whose compared columns differ, expressed as `(a.col IS NOT b.col)` OR-chained across pairs, skipping any pair already consumed as a join key → AND-combine with any pre-existing where clause preserving its params.
**Invariant:** Each left row matches AT MOST ONE right row — the dedup subquery is load-bearing; porters who join directly against a duplicate-rich right table get quadratic result blowup. `IS NOT` (not `!=`) is required so NULL vs non-NULL counts as a difference. The skip-join-pairs check (`joinColumns.get(rightColId) === leftColId`) prevents comparing a column against itself. Trusted-caller-only: it assembles SQL strings from identifiers, never user data.
**Probe:** No direct unit test for `buildComparisonQuery` itself (coverage caveat — exercised only through ActiveDocImport's incremental-import path). Deterministic source probes: `grep -n "MIN(id) AS id" app/server/lib/ExpandedQuery.ts` hits :213 exactly once; `grep -c "IS NOT" app/server/lib/ExpandedQuery.ts` = 1 (:245).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "buildComparisonQuery incremental import diff", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any SQL-level table sync/diff with possibly-duplicate natural keys: dedupe-subquery → join → recover-full-row → IS NOT difference filter is the whole trick. Adapt key choice (`MIN(id)` assumes ascending ids ≈ insertion order) and the dotted-alias scheme to your host. Omit the params-preserving where merge if your queries carry no parameterized prelude.
