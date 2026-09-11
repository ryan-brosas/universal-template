<!-- capsule-v2 -->
# FROM-clause subquery execution modes — coroutine, materialized table, or direct materialized index?

**Source:** turso (Limbo) MIT `main@def9a060`; Codebase Memory project `turso`. **Question:** How does the emitter choose how a FROM-clause subquery is evaluated and stored, and which subqueries may use their synthesized seek index as storage directly?

## choose_from_clause_subquery_execution_mode + emit_from_clause_subqueries
**Path/Symbol:** `core/translate/subquery.rs` — `FromClauseSubqueryExecutionMode` (:58-62, drift-shifted from :60-64 at `main@d9266124f`), `materialized_from_clause_subquery_storage` (:64-77), `choose_from_clause_subquery_execution_mode` (:1373+, was :1339-1373; compound-SELECT direct-index exclusion comment now :1381-1386), `emit_from_clause_subqueries` (:1529+, pre-materialize CTEs via `pre_materialize_multi_ref_ctes` at :1230, doc "BEFORE emitting any coroutines" :1227-1228), eligibility `core/schema.rs::FromClauseSubquery::supports_direct_index_materialization` + `requires_table_materialization` (schema.rs rewritten in drift wave — resolve by symbol).
**Signature:** `fn choose_from_clause_subquery_execution_mode(operation: &Operation, from_clause_subquery: &FromClauseSubquery) -> FromClauseSubqueryExecutionMode`; eligibility: `matches!(self.plan.as_ref(), Plan::Select(_)) && !self.requires_table_materialization()`.
**Data Shape:** three outcomes — `Coroutine` (streamed per outer row), `MaterializedTable` (`QueryDestination::EphemeralTable`), `DirectMaterializedIndex(DirectMaterializedSubquery { index, affinity_str })` where the ephemeral index built for a later seek IS the result store.

### Decisive source
```rust
// subquery.rs:1350-1355 — why compound SELECTs are excluded
// Compound SELECTs still need their own internal ephemeral indexes for
// UNION/INTERSECT/EXCEPT bookkeeping. Reusing the subquery's synthesized
// seek index as the storage target would collapse those roles together and
// break set-operation semantics, so keep the direct-index fast path limited
// to simple SELECT plans.
let can_direct_materialize_index =
    from_clause_subquery.supports_direct_index_materialization();
```

**Flow:** emit order = join_order first, then hash-join build tables not already visited; multi-ref/hinted CTEs are PRE-materialized before any coroutine body is emitted so a coroutine never `OpenDup`s a CTE whose backing table does not exist yet → per table, mode is chosen: ephemeral-index Seek + simple SELECT ⇒ DirectMaterializedIndex (carrying the synthesized seek affinity string); other ephemeral seeks or forced materialization (shared CTE refs / MATERIALIZED hint) ⇒ MaterializedTable; else Coroutine.
**Invariant:** direct-index mode fuses two roles in ONE structure (storage + seek target), so it must be gated on plan simplicity — compound plans keep separate set-operation indexes. The affinity string is captured at CHOOSE time from the seek definition because emission of the index fill must match what the later SEARCH compares against. Shared-materialization annotation counts references across the whole query tree but EXCLUDES correlated post-write RETURNING subqueries from the shared count (:100-116) since they run once per updated row.
**Probe:** text anchors: `grep -c 'fn choose_from_clause_subquery_execution_mode' core/translate/subquery.rs` → 1; `grep -c 'collapse those roles together' core/translate/subquery.rs` → 1; `grep -c 'fn supports_direct_index_materialization' core/schema.rs` → 1 (paired doc-comment test at schema.rs :4090-4095 pins the simple-SELECT-only rule); behavior exercised via `tests/integration/query_processing/test_hash_join_materialization.rs` FROM-subquery LEFT JOIN case (:22).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "choose_from_clause_subquery_execution_mode DirectMaterializedIndex coroutine", limit: 10 });
```

## Verdict
Adopt the three-mode decision ladder and the pre-materialize-CTEs-before-coroutines ordering; adapt the coroutine protocol to your VM's yield model; omit EXPLAIN label formatting.
