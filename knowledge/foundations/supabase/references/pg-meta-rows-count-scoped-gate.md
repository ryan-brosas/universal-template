<!-- capsule-v2 -->
# pg-meta rows-count scoped gate — how do you decide exact count vs estimate when reltuples = -1 means both "empty" and "bulk-loaded"?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** A dashboard row-count must be fast on huge tables but exact on small ones; Postgres's `reltuples = -1` (never analyzed) covers BOTH an empty new table and a freshly bulk-loaded 60k-row table — what gate distinguishes them, and how does the rewrite ship without breaking flag-off traffic?

## The heap-size gate for never-analyzed tables (`packages/pg-meta/src/sql/studio/database/rows.ts`)
**Path/Symbol:** `packages/pg-meta/src/sql/studio/database/rows.ts` : `getTableRowsCountSql` (:13-179), scoped read-only branch (:68-99), scoped non-read-only branch (:120-155); `get-count-estimate.ts` : `THRESHOLD_COUNT` (:3), `THRESHOLD_ESTIMATE_BYTES` (:13), `COUNT_ESTIMATE_SQL` (:18-29).
**Signature:** `getTableRowsCountSql({ table, filters?, enforceExactCount?, isReadOnlyContext?, scoped? }): SafeSqlFragment`.
**Data Shape:** decision matrix over `(reltuples, heap bytes)`: estimate > THRESHOLD_COUNT (50000) → estimate; estimate = -1 AND bytes > THRESHOLD_ESTIMATE_BYTES (50000 × 200 ≈ 10MB, "an exact count over that is subsecond") → estimate; else exact `count(*)`. The byte gate reads REAL heap size: `case when relkind = 'p' then (select coalesce(sum(pg_relation_size(relid)), 0) from pg_partition_tree(oid)) else pg_relation_size(oid) end` — a partitioned PARENT has no storage of its own (size 0), so its size is the sum over pg_partition_tree; pg_partition_tree returns NO rows for a plain non-partitioned table, so it cannot be used unconditionally; views/foreign tables yield 0 → exact count, unchanged behavior. The CASE value and the `is_estimate` flag SHARE the same condition so the reported value and flag can never drift.

### Decisive source
```sql
with approximation as (
    select
      reltuples as estimate,
      -- Whole-tree heap size. A partitioned PARENT (relkind 'p') has no storage
      -- of its own, so its size is the sum over pg_partition_tree; every other
      -- relkind uses its own heap directly (pg_partition_tree returns NO rows
      -- for a plain non-partitioned table, so it cannot be used unconditionally).
      -- Views/foreign tables yield 0 (-> exact count, unchanged behavior).
      case when relkind = 'p'
        then (select coalesce(sum(pg_relation_size(relid)), 0) from pg_partition_tree(oid))
        else pg_relation_size(oid)
      end as bytes
    from pg_class
    where oid = ${literal(table.id)}
)
select
  case
    when estimate > ${literal(THRESHOLD_COUNT)} or (estimate = -1 and bytes > ${literal(THRESHOLD_ESTIMATE_BYTES)}) then -1
    else (${countBaseSqlWithoutSemicolon})
  end as count,
  (estimate > ${literal(THRESHOLD_COUNT)} or (estimate = -1 and bytes > ${literal(THRESHOLD_ESTIMATE_BYTES)})) as is_estimate
from approximation;
```

**Flow:** enforceExactCount short-circuits to a real count in all modes → else build the filtered select/count base SQL via the pass-2 Query builder → branch on isReadOnlyContext × scoped: read-only CANNOT create the pg_temp.count_estimate function, so an over-gate never-analyzed table reports -1 as an estimate instead of running a timing-out exact count; non-read-only scoped calls `pg_temp.count_estimate(${literal(selectBaseSql)})` (EXPLAIN FORMAT JSON → Plan Rows).
**Invariant:** a statistics-based fast path must gate on PHYSICAL size when the statistic is ambiguous (-1 means both empty and huge); partitioned parents need the tree-sum or they misclassify as small; and the value/flag pair must share one condition.
**Probe:** `packages/pg-meta/test/sql/studio/rows-count.test.ts` (369L, read whole; DB-backed — standing runner block, never claimed passing): full matrix — empty/small/bulk/partitioned never-analyzed × scoped/legacy/read-only, with the intentional divergence asserted separately ("scoped INTENTIONALLY diverges from legacy: large never-analyzed table -> estimate" while legacy still exact-counts 60000).

## literal()-quoted embedded select survives any standard_conforming_strings
**Path/Symbol:** `rows.ts` : scoped estimate call (:126-155); legacy twin (:157-179).
**Signature:** n/a — rendering detail of the estimate branch.
**Data Shape:** the filtered SELECT is embedded INSIDE the `pg_temp.count_estimate(...)` call as a string argument. The scoped path quotes it with `literal()` ("literal() quotes the embedded select so backslash identifiers survive under any standard_conforming_strings"); the FROZEN legacy path uses apostrophe-only escaping (`${selectBaseSqlWithoutSemicolon.replaceAll("'", "''")}`), which mangles backslash identifiers when `standard_conforming_strings = off`.

### Decisive source
```ts
// estimate = -1 (never analyzed) gated on heap size (see CTE): large ->
// EXPLAIN estimate, small/empty -> exact count (avoids Postgres's ~10-page
// phantom estimate). Over-threshold keeps legacy behavior. CASE and flag
// share the condition. literal() quotes the embedded select so backslash
// identifiers survive under any standard_conforming_strings.
const estimateExpr = safeSql`pg_temp.count_estimate(${literal(selectBaseSqlWithoutSemicolon)})`
```

**Flow:** test creates `public."wei\rd"("col\umn")`, analyzes it (> threshold + filter → estimate branch), runs scoped with scs on AND off (both pass), then asserts the LEGACY rendering REJECTS under scs=off — pinning the fix by its failure mode.
**Invariant:** when you embed SQL-in-SQL as a string argument, quote the inner SQL with your full literal escaper (E'' prefix + doubled backslashes), not apostrophe-doubling alone — session GUCs like standard_conforming_strings change which escaping is correct, and only the full escaper is correct under both.
**Probe:** rows-count.test.ts "scoped estimate path quotes the embedded select safely (backslash names, scs on & off)" — DB-backed, standing runner block.

## Frozen-twin family at template scale (`table-definition.ts`, `table-editor/table.ts`)
**Path/Symbol:** `packages/pg-meta/src/sql/studio/database/table-definition.ts` : `LEGACY_PG_GET_TABLEDEF_SQL` (:30), `SCOPED_PG_GET_TABLEDEF_SQL` (:725), `createPgGetTabledefSql` (:1437-1440); `sql/studio/table-editor/table.ts` : frozen legacy arm (:348).
**Signature:** `createPgGetTabledefSql({ scoped = false }): SafeSqlFragment` → `scoped ? SCOPED_... : LEGACY_...`.
**Data Shape:** the two branches are kept as COMPLETE STANDALONE templates (no interpolated conditional fragments) "so each rendered statement is easy to read and diff"; PR #47894 replaced three O(catalog) information_schema scans (and a relnamespace::regnamespace cast per pg_class row) with direct string tests and an OID-scoped partial-index lookup, gated behind `scoped` (default false = byte-equivalent to pre-PR). The same frozen-twin pattern recurs in table-editor/table.ts (:348 ternary arm) — the pass-4 pg-meta-entity-retrieve-scoped-oid capsule documents the tables.ts instance of this family.

### Decisive source
```ts
export const createPgGetTabledefSql = ({
  scoped = false,
}: { scoped?: boolean } = {}): SafeSqlFragment =>
  scoped ? SCOPED_PG_GET_TABLEDEF_SQL : LEGACY_PG_GET_TABLEDEF_SQL
```

**Flow:** every consumer (getTableDefinitionSql, getEntityDefinitionsSql, table-editor entity query) threads the same `scoped` flag into the template selector; flag-off traffic gets the frozen legacy rendering byte-for-byte.
**Invariant:** for a large generated SQL template, keep the old and new renderings as whole standalone constants selected by one flag — inline conditional fragments make neither form diffable against production behavior, which is exactly what the flag-off contract requires.
**Probe:** direct read at the pin; grep confirms the FROZEN comment family spans rows.ts (:101, :157), get-count-estimate.ts (:15), table-definition.ts (:27), table-editor/table.ts (:348) plus the pass-4-cited files.

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct source reads plus the direct test at the pin. Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "getTableRowsCountSql THRESHOLD_ESTIMATE_BYTES pg_partition_tree COUNT_ESTIMATE_SQL createPgGetTabledefSql", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: the physical-size gate for ambiguous statistics (-1 ⇒ measure the heap, with partition-tree sum for parents); shared-condition value/flag pairs; the read-only degradation ladder (cannot create helper function ⇒ report sentinel estimate instead of timing out); literal()-quoted SQL-in-SQL embedding; and the standalone-template frozen twin selected by one flag. Adapt thresholds to your row-size profile (the 200 bytes/row constant is a conservative Supabase choice). Omit nothing structural: gating on reltuples alone is the classic mistake this capsule exists to prevent — -1 is ambiguous by construction. Direct-test caveat: rows-count.test.ts (369L) read whole under the standing DB runner block — never claimed passing.
