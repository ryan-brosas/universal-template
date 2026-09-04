<!-- capsule-v2 -->
# Materialized hash-build inputs — when must a hash join's build side be pre-materialized, and as what?

**Source:** turso (Limbo) MIT `main@def9a060`; Codebase Memory project `turso`. **Question:** How does the SELECT emitter materialize a hash join build input into an ephemeral table without losing multiplicity or prefix correlation?

## emit_materialized_build_inputs + rowid-only vs key+payload modes
**Path/Symbol:** `core/translate/emitter/select.rs` — `emit_materialized_build_inputs` (:324, start unchanged at `main@d9266124f`; body shifted), `prune_join_order_for_materialized_inputs` (:572, was :579), `materialization_prefix` (:634, was :641), `collect_materialized_payload_columns` (:695, was :702), `build_materialized_input_columns` (:733, was :740), `build_materialized_build_input_plan` (:761, was :768); call site at top of `emit_program_for_select_with_resolver` (:44).
**Signature:** `pub(crate) fn emit_materialized_build_inputs(program, resolver, plan: &mut SelectPlan) -> Result<HashMap<usize, MaterializedBuildInput>>`; mode enum `MaterializedBuildInputMode::{RowidOnly, KeyPayload { num_keys, payload_columns }}`.
**Data Shape:** one ephemeral BTreeTable per materialization (`hash_build_input_{id}`, HAS_ROWID); RowidOnly schema = `[rowid]`, KeyPayload = `key_0..key_{n}` (BLOB) then `payload_i` (RowId→INTEGER else BLOB).

### Decisive source
```rust
// select.rs:371-399 — WHY the mode split exists (condensed from the verbatim comment)
// Rowid-only keeps each build-table rowid at most once. That throws away
// which prefix row it came from … every t1 row matches both t2 rows,
// incorrectly producing 4 rows (a cross product).
// Therefore: if the prefix has other tables, we must store key+payload
// rows so each prefix match stays distinct and the main plan can drop
// the prefix loops.
if build_table_was_prior_probe || prefix_has_other_tables {
    // KeyPayload: keys + payload columns of the whole join prefix
} else {
    // RowidOnly: single-table prefix keeps filters without multiplicity loss
}
```

**Flow:** for each HashJoin flagged `materialize_build_input` → compute the join PREFIX (tables before probe in join order + the build table) → choose mode (prior-probe chaining or multi-table prefix ⇒ KeyPayload; single-table ⇒ RowidOnly) → emit a NESTED subplan (`program.nested`) writing into the ephemeral table via `QueryDestination::EphemeralTable`, saving/restoring `result_columns`/`table_references` around it and keeping hash tables open across subplans → after all subplans, PRUNE the main join order of prefix tables already captured by KeyPayload materializations and mark their WHERE terms consumed (except OUTER-JOIN-owned terms :609-620).
**Invariant:** RowidOnly is only legal when the prefix is exactly the build table — any extra prefix table destroys t1→t2 correlation (cross-product bug). The subplan must SANITIZE cloned access methods: any Seek/RowidEq/IndexMethod/VTab-constraint expression referencing tables outside the prefix downgrades to a default scan (:842-913), and the subplan resets `consumed` flags on its WHERE clone because parent-plan consumption reflects access methods that no longer exist inside the subplan (:790-805). Recursive materialization is disabled by flipping the inner HashJoin back to a scan (:813-818). A debug turso_assert (:536-570) enforces pruned prefixes never linger in the join order.
**Probe:** `tests/integration/query_processing/test_hash_join_materialization.rs::hash_join_materialization_preserves_left_join_correlation` (:22 — exactly the cross-product regression), `::hash_join_unmatched_rows_apply_payload_backed_predicates` (:297); text anchors: `grep -c 'MATERIALIZE hash build input for' core/translate/emitter/select.rs` → 1; `grep -c 'Rowid-only keeps each build-table rowid at most once' core/translate/emitter/select.rs` → 1; `grep -c 'materialized build input prefix table still present in join order' core/translate/emitter/select.rs` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "emit_materialized_build_inputs MaterializedBuildInput hash join", limit: 10 });
```

## Verdict
Adopt the two-mode materialization rule and the prefix-sanitization ladder; adapt ephemeral-table plumbing to your executor; omit EXPLAIN subtree decoration unless porting query-plan output.
