<!-- capsule-v2 -->
# IVM aggregate-state blob codec — how does a group's running aggregate state survive a restart?

**Source:** turso (Limbo) MIT `main@def9a060`; Codebase Memory project `turso`. **Question:** What is the on-disk record layout for incremental-view-maintenance aggregate state, and which decode rules must a porter replicate exactly?

## AggregateState to_value_vector/from_blob
**Path/Symbol:** `core/incremental/aggregate_operator.rs` — `AggregateState` (:463, start unchanged at `main@d9266124f`: count/sums/avgs/mins/maxs/distinct_counts/distinct_sums), `to_value_vector` (:738), `from_value_vector` (:808), `to_blob` (:1004), `from_blob` (:1019); persistence consumer `core/incremental/persistence.rs` (`Value::Blob(blob) => AggregateState::from_blob(&blob)` in state-table column 3).
**Signature:** `fn to_blob(&self, aggregates: &[AggregateFunction], group_key: &[Value]) -> Result<crate::ValueBlob>`; `pub fn from_blob(blob: &[u8]) -> Result<(Self, Vec<Value>)>`.
**Data Shape:** one SQLite record: `[group_key_len:i64] ++ group_key values ++ [count:i64] ++ [num_aggregates:i64] ++ per-aggregate (metadata from AggregateFunction::to_values() + state cells)`. Per-type cells — Count: none; CountDistinct: i64 count; Sum: f64; SumDistinct/AvgDistinct: i64 count + f64 sum; Avg: f64 sum + i64 count; Min/Max: i64 has_value flag then the value ONLY when flag==1.

### Decisive source
```rust
// aggregate_operator.rs:1030-1042 — decode-side validation ladder
let group_key_count = match &all_values[0] {
    Value::Numeric(Numeric::Integer(n)) if *n >= 0 => *n as usize,
    Value::Numeric(Numeric::Integer(n)) =>
        return Err(InternalError(format!("Negative group key count: {n}"))),
    other => return Err(...),
};
// :785-791 encode side — MIN/MAX are OPTIONAL-valued:
if let Some(min_val) = self.mins.get(col_idx) {
    values.push(Value::from_i64(1)); // Has value
    values.push(min_val.clone());
} else {
    values.push(Value::from_i64(0)); // No value  → NO value cell follows
}
```

**Flow:** delta application mutates in-memory maps → at commit the operator serializes each group via to_blob and writes it as column 3 of the DBSP state table row keyed by (operator_id, zset_hash, element_id) → after restart, ReadRecord fetches the blob and `from_blob` reconstructs `(state, group_key)` positionally.
**Invariant:** the layout is SELF-DESCRIBING but POSITIONAL — readers walk it with a cursor in exactly the encoder's order; there is no tag per cell beyond the per-aggregate metadata. Two asymmetries are load-bearing: (1) MIN/MAX emit a has_value flag and OMIT the value cell when absent — a decoder that always reads a value desynchronizes every later field; (2) COUNT is global (stored once at the head), not per-aggregate-cell. Multiple DISTINCT aggregates over the SAME column dedupe their updates through `ColumnMask` processed_counts/processed_sums during apply_delta (:1082-1083) so counts stay exact. Weight arithmetic is signed (`apply_delta(values, weight: isize, …)`) — deletes subtract.
**Probe:** text anchors (no dedicated upstream unit test for the codec; exercised via persistence tests): `grep -c 'Negative group key count' core/incremental/aggregate_operator.rs` → 1; `grep -c 'all_values.push(Value::from_i64(group_key.len() as i64))' core/incremental/aggregate_operator.rs` → 1; `grep -c 'values.push(Value::from_i64(self.count))' core/incremental/aggregate_operator.rs` → 1; `grep -c 'AggregateState::from_blob(&blob)' core/incremental/persistence.rs` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "AggregateState from_blob aggregate state blob", limit: 10 });
```

## Verdict
Adopt the positional self-describing layout with the has_value-flag omission rule for optional aggregates; adapt Value encoding to your host; omit the yield-injection test scaffolding (`yield_test_support`) unless porting resumable IVM commits. Coverage caveat: codec verified by grep anchors + persistence-suite usage, not a dedicated roundtrip unit test upstream.
