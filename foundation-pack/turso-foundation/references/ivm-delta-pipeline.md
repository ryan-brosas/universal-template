<!-- capsule-v2 -->
# IVM delta pipeline — how does a materialized view stay current across transactions?

**Source:** turso (Limbo) MIT `main@def9a060`; Codebase Memory project `turso`. **Question:** How do row mutations become per-table deltas, and how are they merged into the view's b-tree at commit?

## ViewTransactionState → apply_view_deltas → DbspCircuit::commit
**Path/Symbol:** capture: `core/vdbe/execute.rs` op-side `view_transaction_states.get_or_create(view_name)` + `tx_state.insert/delete(table_name, key, values)` (:12050+, drift-shifted from :11770 at `main@d9266124f`); merge driver: `core/vdbe/mod.rs:Program::apply_view_deltas` (:2168, was :2000-2102); circuit commit: `core/incremental/compiler.rs:DbspCircuit::commit` (:533, start unchanged) with `WriteRowView` state machine; view shell: `core/incremental/view.rs:IncrementalView` (:201) + `merge_delta` (:1404).
**Signature:** `fn apply_view_deltas(&self, state: &mut ProgramState, rollback: bool, pager: &Arc<Pager>) -> Result<IOResult<()>>`; `pub fn merge_delta(&mut self, delta_set: DeltaSet, pager: Arc<Pager>) -> Result<IOResult<()>>`.
**Data Shape:** per-transaction `ViewTransactionState { table_deltas: HashMap<String, Delta> }` (RefCell-backed; insert/delete append `(HashableRow, ±1)` entries). Circuit state table = 5 columns `(operator_id i64, zset_id i64, element_id i64, value Blob/Null, weight isize)` (`OPERATOR_COLUMNS=5`, unique index `dbsp_state_pk(operator_id,zset_id,element_id)`); view b-tree rows carry the view's columns + trailing weight.

### Decisive source
```rust
// core/vdbe/mod.rs — rollback DISCARDS, commit merges per view in order
if rollback {
    self.connection.view_transaction_states.clear();
    return Ok(IOResult::Done(()));
}
turso_assert_ne!(root_page, 0, "Materialized view should have a root page");
...
match view.merge_delta(delta_set, pager.clone())? {
    IOResult::Done(_) => { /* advance to next view */ }
    IOResult::IO(io)  => return Ok(IOResult::IO(io)),   // resume at same index
}
```
```rust
// core/incremental/compiler.rs::DbspCircuit::commit — ownership dance around &mut self
let mut state = std::mem::replace(&mut self.commit_state, CommitState::Init);
... CommitState::CommitOperators { .. } =>
    return_and_restore_if_io!(&mut self.commit_state, state,
        self.run_circuit(execute_state, &pager, state_cursors, true));
... CommitState::UpdateView { .. } => write_row_state.write_row(...)  // GetRecord→Delete|Insert{final_weight}
```

**Flow:** every INSERT/UPDATE/DELETE opcode pushes old-record deletes then new-record inserts into each DEPENDENT view's tx state → at commit, apply_view_deltas iterates views (IO resumes at same index) → circuit runs operators over the DeltaSet producing an output Delta → for each change row, WriteRowView seeks the view b-tree by rowid, reads the LAST value as existing weight, computes `final_weight = existing + weight`: ≤0 deletes the row, >0 rewrites with new weight. Fresh cursor per GetRecord ("btree cursor state machine limitations").
**Invariant:** Updates MUST be captured as ordered delete-then-insert pairs on FULL row values (see dbsp.rs comment: using only row keys makes a filter-invalidating update cancel to nothing — "(5, w=-1),(5,w=+1) disappears"); weights are the Z-set multiplicities, never booleans.
**Probe:** `testing/sqltests/tests/ivm-compound-null-filter.sqltest` (4 expect blocks incl. update-to-null emptying the view; requires materialized_views feature, skipped under MVCC mode). Text anchors: `grep -c 'DBSP_CIRCUIT_VERSION: u32 = 1' core/incremental/compiler.rs` → 1; `grep -c 'SELECT {select_clause} FROM {table_name}' core/incremental/view.rs` → 2. Unit tests: dbsp.rs `test_zset_represents_updates_as_delete_plus_insert` (:482).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "apply_view_deltas merge_delta ViewTransactionState", limit: 10 });
```

## Verdict
Adopt weighted-delta capture keyed by dependent views and the seek-read-weight-write merge machine. Adapt storage layout if host lacks b-tree weight column. Omit population-time query generation nuances beyond what generate_populate_queries pins (per-table SELECT with OR-combined conditions, `*, rowid` when no rowid alias).
