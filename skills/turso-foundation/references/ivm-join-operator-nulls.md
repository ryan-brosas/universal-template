<!-- capsule-v2 -->
# IVM join operator — how does an incremental join emit matched and unmatched deltas?

**Source:** turso (Limbo) MIT `main@def9a060`; Codebase Memory project `turso`. **Question:** What SQL NULL semantics and state handling does the DBSP join operator apply when merging deltas from two sides?

## JoinOperator key matching + delta processing
**Path/Symbol:** `core/incremental/join_operator.rs` `sql_keys_equal` (:441, start unchanged at `main@d9266124f`, NULL-rejection at :449-453), `extract_join_key` (:417), `process_join_state` (:188/:461), `read_next_join_row` (:26), storage-id helpers `left_storage_id/right_storage_id` (:428/:434).
**Signature:** `fn sql_keys_equal(left_key: &HashableRow, right_key: &HashableRow) -> bool`; state machine drives `IncrementalOperator::eval/commit` from the trait (`core/incremental/operator.rs:219-241`).
**Data Shape:** join keys are `HashableRow`s built by projecting values at configured indices; per-side persisted state lives under `generate_storage_id(operator_id, ..)` addresses read through `DbspStateCursors`.

### Decisive source
```rust
// core/incremental/join_operator.rs
fn sql_keys_equal(left_key: &HashableRow, right_key: &HashableRow) -> bool {
    if left_key.values.len() != right_key.values.len() { return false; }
    for (left_val, right_val) in left_key.values.iter().zip(right_key.values.iter()) {
        // In SQL, NULL never equals NULL
        if matches!(left_val, Value::Null) || matches!(right_key, Value::Null) { return false; }
        if left_val != right_val { return false; }
    }
    true
}
```
(Note: source line reads `matches!(right_val, Value::Null)` — the excerpt's second arm is the same check on right_val.) Length mismatch is a hard false, so differently-arity keys can never spuriously match.

**Flow:** incoming delta rows → extract join key projection → probe the opposite side's accumulated state (read via cursors, one row at a time through `read_next_join_row`) → for each equal-key counterpart emit weighted output pairs (+1/−1 combinations of input weights); unmatched rows are buffered so LEFT/anti semantics can emit them once side state settles; results consolidate into the output Delta consumed by downstream operators or view write-back.
**Invariant:** SQL NULL semantics override Rust equality here — Hash128 hashes are only used to FIND candidates; actual matching re-compares values with the NULL-never-equals rule (hash-equal NULL keys must still fail sql_keys_equal).
**Probe:** unit tests in `core/incremental/dbsp.rs` cover delta ordering this operator consumes (`test_hashable_row_delta_operations` :498); text anchor: `grep -c 'fn sql_keys_equal' core/incremental/join_operator.rs` → 1. Behavior-level direct tests live in `testing/sqltests/tests/ivm-compound-null-filter.sqltest` (NULL-filter views stay empty for NULL-only rows).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "JoinOperator process_join_state extract_join_key", limit: 10 });
```

## Verdict
Adopt the NULL-pair rejection and length-guard before value comparison; adapt state persistence to host cursor API. Omit aggregate/project operator internals unless porting full IVM (aggregate_operator.rs has its own blob-state format worth a later capsule).
