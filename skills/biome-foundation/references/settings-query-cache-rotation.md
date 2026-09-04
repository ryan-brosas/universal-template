<!-- capsule-v2 -->
# Bounded settings-query cache — rotating an incremental engine's storage when interned values leak growth

**Source:** biome MIT `main@88f805e19b67`; Codebase Memory `biome`. **Question:** Short-lived queries into a memoization engine interne keys forever; how do you bound that growth without blocking the read hot path?

## SettingsQueryCache rotation
**Path/Symbol:** `crates/biome_service/src/db/mod.rs:35-130`; capacity `:35` (`SETTINGS_QUERY_CACHE_CAPACITY: usize = 256`); rotate `:92-115` (`SettingsQueryCache::database`); counter wiring `:67-90`; direct test `settings_query_cache_rotates_storage_at_capacity` :1012.
**Signature:** `fn database(&self) -> SettingsQueryDb` on `struct SettingsQueryCache { state: RwLock<SettingsQueryCacheState>, event_handler: Option<...> }`.

### Decisive source
```rust
// :94-114 — read-lock fast path; write lock only to swap in FRESH storage, re-checked
{
    let state = self.state.read().unwrap_or_else(std::sync::PoisonError::into_inner);
    if state.interned_values.load(Ordering::Relaxed) < SETTINGS_QUERY_CACHE_CAPACITY {
        return state.database();
    }
}
let mut state = self.state.write().unwrap_or_else(std::sync::PoisonError::into_inner);
if state.interned_values.load(Ordering::Relaxed) >= SETTINGS_QUERY_CACHE_CAPACITY {
    *state = SettingsQueryCacheState::new(
        self.event_handler.as_ref().map(|handler| std::panic::AssertUnwindSafe(handler.0.clone())),
    );
}
state.database()
// :71-78 — the counter is fed by a salsa event hook, not by call sites
if matches!(&event.kind, salsa::EventKind::DidInternValue { .. }) {
    counter.fetch_add(1, Ordering::Relaxed);
}
```

**Flow:** every db acquisition goes through `database()` → under a READ lock: if interned count < 256, hand out a clone of current storage (hot path never writes) → at capacity: WRITE lock, re-check (another thread may have rotated), replace the entire `SettingsQueryCacheState` with fresh storage → memoized settings queries restart from empty.
**Invariant:** Rotation is wholesale (drop all cached queries), never partial eviction — simpler and safe because these are pure derived queries. The event-handler closure is cloned through `AssertUnwindSafe` so the new storage keeps counting. Double-check under the write lock prevents double rotation. Counting rides engine events (DidInternValue), so no query site needs instrumentation.
**Probe:** `grep -n 'SETTINGS_QUERY_CACHE_CAPACITY' crates/biome_service/src/db/mod.rs` → exactly `:35`, `:99`, `:107`, test loop `:1016`; `grep -n 'DidInternValue' crates/biome_service/src/db/mod.rs` → single hit `:72`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "SettingsQueryCache interned_values rotate storage", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: capacity-triggered whole-store rotation with read-fast/write-rare locking and event-driven accounting for any cache whose entries you cannot evict individually. Adapt threshold to workload (256 suits per-op settings lookups). Omit if your engine already supports LRU or explicit invalidation of interned values.
