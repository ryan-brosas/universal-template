<!-- capsule-v2 -->
# Grace hash-join executor — how does the runtime spill a hash join that exceeds memory?

**Source:** turso (Limbo) MIT `main@def9a060`; Codebase Memory project `turso`. **Question:** What partition-count policy, spill ordering, and probe NULL semantics must the executor preserve?

## HashTable build/probe with adaptive grace partitioning
**Path/Symbol:** `core/vdbe/hash_table.rs:HashTable::finalize_build` (:1806-1860), `probe` (:1867+), `choose_partition_count` (:1105-1125), `redistribute_to_partitions` (:1419-1432), `next_partition_to_spill` (:1441-1451), key hashing `hash_join_key` (:66-118).
**Signature:** `pub fn finalize_build(&mut self, metrics: Option<&mut HashJoinMetrics>) -> Result<IOResult<()>>`; `pub fn probe(&mut self, probe_keys: Vec<Value>, metrics: Option<&mut HashJoinMetrics>) -> Result<Option<&HashEntry>>`.
**Data Shape:** constants: `DEFAULT_SEED: u64 = 1337`, `DEFAULT_MEM_BUDGET` 32KB under debug_assertions (deliberately small "to trigger frequent spilling during tests") / 64MB release, `DEFAULT_BUCKETS=1024`, `MIN_PARTITIONS=16`, `MAX_PARTITIONS=128`. States: `HashTableState::{Building, Spilled, Probing}`.

### Decisive source
```rust
// core/vdbe/hash_table.rs — adaptive partition sizing
let avg_entry_size = if self.num_entries > 0 {
    (self.mem_used / self.num_entries).max(entry_size)
} else { entry_size.max(1) };
let target_partition_bytes = (self.mem_budget / 2).max(avg_entry_size);
let target_entries_per_partition = (target_partition_bytes / avg_entry_size).max(1);
let estimated_total_entries = self.num_entries.saturating_add(1);
let mut partitions = estimated_total_entries.div_ceil(target_entries_per_partition);
partitions = partitions.clamp(MIN_PARTITIONS, MAX_PARTITIONS);
partitions.next_power_of_two()
```
```rust
// finalize_build: wait pending writes, then split partitions by on-disk vs memory
for partition_idx in spill_targets {           // find_partition(...) == Some
    if let Some(completion) = self.spill_partition(partition_idx, ...)? {
        if !completion.finished() { io_yield_one!(completion); }
    }
}
for partition_idx in materialize_targets {     // empty-on-disk but buffered rows
    self.materialize_partition_in_memory(partition_idx)?;
}
self.state = HashTableState::Probing;
```

**Flow:** build inserts into buckets; on budget overflow redistribute all bucket entries into partition buffers keyed by high bits of the entry hash (`partitioning.index(hash)`), clearing matched_bits ("spilled partitions will have their own"). Spill selection is always LARGEST non-empty buffer. Probe: any NULL key returns None immediately (`NULL != NULL in SQL`); hash via rapidhash seed 1337 honoring collations (integers hash as FLOAT when exactly f64-representable so `10` matches `10.0`; NOCASE lowercases ASCII only, stopping at NUL); spilled mode loads one partition at a time through an LRU and iterates matches via `probe_entry_idx`.
**Invariant:** Partition count MUST be a power of two (asserted even for overrides) because partition_index masks hash bits; the debug budget shrink is load-bearing for test coverage — porting only the 64MB constant silently disables every spill test.
**Probe:** `core/vdbe/hash_table.rs::test_adaptive_partition_count_bounds` (:3659 — forced spill then asserts power-of-two within [16,128]); `test_hash_table_spill_and_load_partition_round_trip` (:3978). Text anchors: `grep -c 'DEFAULT_SEED: u64 = 1337' core/vdbe/hash_table.rs` → 1; `grep -c 'partitions.next_power_of_two()' core/vdbe/hash_table.rs` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "HashTable finalize_build spill_partition choose_partition_count", limit: 10 });
```

## Verdict
Adopt adaptive power-of-two partitioning, largest-first spill order, integer/float hash unification, and the NULL-probe short-circuit. Adapt TempFile/temp_store plumbing to host IO. Omit metrics export shape.
