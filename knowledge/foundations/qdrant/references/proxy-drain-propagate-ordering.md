<!-- capsule-v2 -->
# Propagate-to-wrapped drain — in what order and under which lock does a proxy replay its buffers into the frozen segment?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** At unproxy/snapshot time, how are buffered index changes, vector-name intents, and deletes applied to the wrapped segment without deadlocking search or losing deletes?

## Three ordered phases under one upgradable-read lock
**Path/Symbol:** `lib/shard/src/proxy_segment/mod.rs`: `ProxySegment::propagate_to_wrapped` (:246-357). Drain consumers (trace_path inbound): `lib/shard/src/segment_holder/snapshot.rs`: `try_unproxy_segment`, `unproxy_all_segments`; `lib/collection/src/shards/local_shard/snapshot.rs`: `proxy_all_segments_and_apply`, `snapshot_all_segments`.
**Signature:** `pub fn propagate_to_wrapped(&mut self) -> OperationResult<()>`.
**Data Shape:** consumes-and-clears three buffers: `changed_indexes` (per-field), `changed_vector_names` (per-name intents), `deleted_points` (id → versions); resets `deleted_deferred_count`.

### Decisive source
```rust
// :247-253 — locking strategy (PR #4206 deadlock):
// we must not keep a write lock on the wrapped segment ... The search functions
// conflict with it trying to take a read lock on the wrapped segment as well while
// already holding the deleted points lock ... Instead we just take an upgradable
// read lock, upgrading to a write lock on demand.
let mut wrapped_segment = wrapped_segment.upgradable_read();
// Phase order comment: :255-257 — "Propagate index changes BEFORE point deletions:
// point deletions bump the segment version, can cause index changes to be ignored"
// Phase 2 (:289-313): Present { supersedes_wrapped: true } ⇒ delete_vector_name FIRST,
//   "create_vector_name_impl is idempotent and would silently keep the wrapped's stale storage"
// Phase 3 (:322-341): queued deletes may be OLDER than wrapped state — "Such deletes are
//   ignored because the point in the wrapped segment is considered to be newer. This is
//   possible because different proxy segments can share state through a common write
//   segment" (PR #7208); then: deleted_points.clear(); // mask deliberately NOT cleared:
//   "no performance advantage and does not affect the correctness of search"
```

**Flow:** drain begins with one `upgradable_read` → phase A replays index-change intents in version order under `with_upgraded`, asserts each change version ≥ wrapped segment version, clears buffer → phase B replays vector-name intents, deleting-then-creating superseded names so idempotent create cannot preserve stale bytes → phase C re-deletes buffered points through the wrapped segment's normal version gating (older ones harmlessly ignored), clears the map but keeps the local mask.
**Invariant:** (1) phase order is mandatory — deletes bump the wrapped segment's version, so index changes applied after them would be dropped by version gating; (2) never hold a plain write lock for the whole drain; upgrade on demand or search deadlocks against the deleted-points lock; (3) stale queued deletes must be tolerated, not errors — sibling proxies share the delete set via a common write segment.
**Probe:** no dedicated upstream unit test executes the full three-phase drain; pinned by direct read of :246-357 plus consumer reads (`try_unproxy_segment` :129-170, `unproxy_all_segments` :173-219). Recorded caveat in verification.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "propagate to wrapped changed indexes vector names deleted points unproxy", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ordered intent draining with version-tolerant replay and on-demand lock upgrades. Adapt the specific lock ladder (upgradable_read/with_upgraded is a parking_lot idiom). Omit the double-proxy passthrough case if your host forbids proxy-over-proxy.
