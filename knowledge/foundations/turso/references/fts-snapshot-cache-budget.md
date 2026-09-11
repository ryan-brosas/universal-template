<!-- capsule-v2 -->
# FTS snapshot cache budget — why is admission always-yes but retention bounded, and which eviction order does the budget use?

**Source:** turso (MIT) `main@d9266124f` ($REFERENCE_ROOT/memory/turso); Codebase Memory `turso`. **Question:** How do you bound memory for a library whose synchronous read callbacks cannot fall back to storage I/O — without turning the budget cliff into a cold reload per statement?

## Rejecting a snapshot saves nothing; evict OLDEST after always-inserting
**Path/Symbol:** `core/index_method/fts.rs`: `CachedFtsStates` (:1221-1312: entries Vec, prune :1264-1273, insert :1290-1304, evict_to_fit :1307-1311), `CachedFtsState.matches_snapshot/matches_manifest` (:1235-1254), `FTS_MAX_CACHED_CONNECTIONS = 4` (:88), `FTS_MAX_RETAINED_CACHE_BYTES = 192MiB` (:98), FileCache deliberately-unbounded doc (:501-507).
**Signature:** `fn insert(&mut self, state: CachedFtsState, byte_budget: usize) -> bool` — retains nothing of the rejected kind; pushes ALWAYS, then prunes.
**Data Shape:** per attachment: ≤4 connection-local snapshots (LRU-first Vec), aggregate resident bytes measured ONLY from `directory.hot_cache.size()` (retained-for-reuse memory), never live cursor memory. Two-layer identity: matches_snapshot (MVCC tx id equality; WAL pos equality) decides REUSE eligibility; matches_manifest (incarnation + generation equality against the on-disk control record) decides CURRENCY.

### Decisive source
```rust
// fts.rs:1292-1302 — the counter-intuitive core (verbatim):
self.entries
    .retain(|cached| !Weak::ptr_eq(&cached.connection, &state.connection));
// Always keep the newest snapshot and evict older ones to make room.
// Rejecting an oversized snapshot outright would not save memory —
// the live cursor holds the whole snapshot anyway — it would only
// force the next statement to reload it all from storage, turning
// the budget cliff into a full cold load per statement.
self.entries.push(state);
self.prune();
while self.entries.len() > 1 && self.resident_cache_bytes() > byte_budget {
    self.entries.remove(0);
}
```

**Flow:** insert replaces same-connection entry → push newest → prune dead connections (Weak strong_count == 0), then enforce count cap 4 AND byte budget while keeping ≥1 entry (newest always survives; `entries.len() > 1` guard) → reuse path validates BOTH layers before trusting cached Tantivy directory/reader: wrong snapshot ⇒ rebuild from current one; stale manifest ⇒ full reload + control-record re-validation. Writer cache mirrors this with stricter validation: meta.json compared against btree before ANY reuse because rollback or another connection's write may have moved the btree underneath (:1193-1210 CachedFtsWriter doc).
**Invariant:** the budget bounds RETAINED state only — a running cursor legitimately holds its entire snapshot resident regardless of size, because tantivy's Directory reads are synchronous callbacks that cannot fall back to storage I/O (:501-507). Porters who try to make FileCache itself evicting break reads mid-scan. The test override hook (`set_fts_retained_cache_bytes_for_test`, :107-118) exists precisely so budget-admission rejection is reachable without multi-hundred-MiB indexes — port the seam WITH its testability hook.
**Probe:** `grep -n 'set_fts_retained_cache_bytes_for_test\|cache_admission_rejections' core/index_method/fts.rs` hits :110/:482/:1399; eviction-order behavior pinned by tests/integration/index_method/ via IndexMethodTestStats.cached_connection_count / cached_bytes / cache_admission_rejections (:477-482).
**Retrieve:** search_graph "CachedFtsStates FTS_MAX_RETAINED_CACHE_BYTES matches_snapshot" resolves `turso.core.index_method.fts.CachedFtsStates` core/index_method/fts.rs :1221+ line-exact.

## Verdict
Adopt "admission unconditional, retention bounded, oldest-dies, newest-immune" for any read-through cache over non-evictable engine state. Adapt budgets/count caps to host. Omit the tantivy-specific writer-cache meta.json comparison unless porting FTS wholesale (then see fts-control-record-manifest). Coverage: no_recorded_issue on fts.rs; stats fields give deterministic probes under feature = "test_helper".
