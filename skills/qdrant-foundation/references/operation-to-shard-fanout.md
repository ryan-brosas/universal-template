<!-- capsule-v2 -->
# Operation→shard fan-out — how does one update operation split across shards without losing any point?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** When a collection-level update arrives, how is it partitioned per shard, and what happens to points owned by more than one shard during resharding?

## OperationToShard: ByShard vs ToAll
**Path/Symbol:** `lib/collection/src/operations/mod.rs`: `OperationToShard<O>` (:70-99), `split_iter_by_shard` (:102-121), `point_to_shards` (:131-138).
**Signature:** `fn split_iter_by_shard<I, F, O: Clone>(iter: I, id_extractor: F, ring: &HashRingRouter) -> OperationToShard<Vec<O>>`; `fn point_to_shards(point_id: &ExtendedPointId, ring: &HashRingRouter) -> ShardIds`.
**Data Shape:** `OperationToShard::ByShard(Vec<(ShardId, O)>)` for point-addressable ops; `ToAll(O)` for collection-wide ops (create index etc.). `point_to_shards` returns *multiple* shard ids only while resharding is in progress; otherwise exactly one.

### Decisive source
```rust
// split_iter_by_shard :111-120 — an item is CLONED into every owning shard
for operation in iter {
    for shard_id in point_to_shards(&id_extractor(&operation), ring) {
        op_vec_by_shard
            .entry(shard_id)
            .or_default()
            .push(operation.clone());
    }
}
// point_to_shards :132-136
let shard_ids = ring.get(point_id);
assert!(!shard_ids.is_empty(), "Hash ring is guaranteed to be non-empty");
```

**Flow:** extract each item's point id → hash-ring lookup yields 1..N owning shards → clone the item into each owner's bucket → `OperationToShard::ByShard(buckets)`; non-point ops map to `ToAll` and every shard applies them. `map(f)` rewrites the payload type while preserving the shape (`ByShard` maps per-entry, `ToAll` maps once). `to_none()` is an empty `ByShard` — a legal no-op result.
**Invariant:** (1) during resharding a point can be delivered to two shards — consumers must tolerate duplicate application, which downstream version gating makes idempotent; (2) an empty ring is a panic, not a silent drop; (3) `map` must not collapse `ByShard` into `ToAll` or ordering/sharding semantics break.
**Probe:** direct test surface is the fan-out consumer chain (`ShardHolder.update` → per-shard apply); the unit-pinned assertions here are the `assert!(...)` in `point_to_shards` :133-136 and the clone-per-owner loop read directly at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "OperationToShard split iter by shard point to shards hash ring", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the `ByShard/ToAll` envelope with clone-per-owner fan-out and the multi-shard resharding tolerance. Adapt `HashRingRouter` placement and `ExtendedPointId` typing to your host's sharding key space. Omit the staging-feature op variants behind `#[cfg(feature = "staging")]`.
