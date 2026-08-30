<!-- capsule-v2 -->
# Unsynced proxy finalize window — when must a wrapper's deleted-mask snapshot be taken so a racing write can't ghost points out of KNN?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** A proxy snapshots the wrapped segment's deleted bitvec at construction; what race can silently drop live points from filtered search, and how does the type system close it?

## Two-phase construction: mask synced exactly once, under the freeze lock
**Path/Symbol:** `lib/shard/src/proxy_segment/mod.rs`: type docs + struct (:48-64), `UnsyncedProxySegment::new` (:74-95), `finalize` (:102-105), `sync_deleted_mask` (:140-149).
**Signature:** `pub fn new(segment: LockedSegment) -> Self; pub fn finalize(mut self) -> ProxySegment` (with `#[must_use = "an UnsyncedProxySegment must be turned into a ProxySegment via .finalize()"]`).
**Data Shape:** `deleted_mask: Option<BitVec>` — None until finalize; `finalize` consumes self, so sync cannot be forgotten nor done twice.

### Decisive source
```rust
// :50-61 (type docs, condensed) — deleted_mask is a snapshot of the wrapped
// segment's deleted bitvec. That snapshot is only valid once the wrapped segment
// is frozen under the segment-holder write lock: a proxy is built while only a
// read/upgradable-read lock is held, so an upsert ... can still land on the
// not-yet-frozen wrapped segment afterwards. An upsert landing in that window
// extends the wrapped segment's point count past the snapshot; the scored search
// path then treats every offset beyond deleted_mask as deleted
// (NotDeletedChecker defaults out-of-range to deleted), silently dropping a live
// point from filtered KNN even though scroll/count/retrieve still see it.
pub fn finalize(mut self) -> ProxySegment {   // :102-105
    self.0.sync_deleted_mask();               // fresh read AFTER freeze closes the ghost direction too
    self.0
}
```

**Flow:** optimizer wraps a frozen-bound segment → `new` copies config/version but leaves the mask None → caller takes the segment-holder write lock (wrapped can no longer change) → `finalize()` reads the bitvec once, capturing both the full final point range and any deletes that raced in during construction → only now is the proxy searchable.
**Invariant:** (1) never read the wrapped bitvec before the wrapped segment is frozen — a stale-length mask turns post-snapshot offsets into implicit deletions for scored search while scroll/count disagree; (2) construction and finalization are separate steps because they need different locks; (3) the compiler enforces the ordering via `#[must_use]` + consuming finalize.
**Probe:** direct test READ WHOLE `lib/shard/src/proxy_segment/tests.rs::test_proxy_deleted_mask_resync_after_race_window_write` (:66-162): builds an unsynced proxy over a 2-point segment, then runs BOTH orderings — `finalize()` before a race write of point 3 ⇒ KNN misses it (`assert!(!buggy_ids.contains(&3.into()))`, commented "buggily dropped"); race write before `finalize()` ⇒ KNN finds it; the proxy-deleted point 1 stays excluded in both.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "UnsyncedProxySegment finalize deleted mask snapshot frozen wrapped segment race", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern: any cached-from-source summary structure built under optimistic locks should be constructed in two phases with a consuming, `#[must_use]` finalizer that re-reads after freeze. Adapt which lock counts as "frozen" in your holder. Omit qdrant's `NotDeletedChecker` default-deleted semantics unless you port its scored-search checker too.
