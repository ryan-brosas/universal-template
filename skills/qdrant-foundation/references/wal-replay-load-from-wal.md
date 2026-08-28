<!-- capsule-v2 -->
# WAL replay at shard load — how does a restart re-apply only what is unapplied, without losing acknowledged data?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** After a crash, which WAL entries must be re-applied synchronously before the shard serves reads, which may be handed to the update worker, and how does a stale persisted applied-seq or a truncated WAL keep the replay window valid?

## Synchronous replay of [first_index, to) with an optional worker-routed tail
**Path/Symbol:** `lib/collection/src/shards/local_shard/mod.rs`: `LocalShard::load_from_wal` (:734-1003), `insert_fake_operation` (:722-727); tests `lib/collection/src/tests/wal_recovery_test.rs` (see Probe).
**Signature:** `pub async fn load_from_wal(&self, collection_id: CollectionId) -> CollectionResult<()>`.
**Data Shape:** `from = wal.first_index()` (truncation already skipped the durable prefix); `last_wal_index = from + wal.len(false)`; replay window `[from, to)`; tail `[to, last_wal_index)` enqueued to the update channel.

### Decisive source
```rust
// :755-762 — applied_seq is honored ONLY under prevent_unoptimized:
let op_num_upper_bound = if prevent_unoptimized {
    self.applied_seq_handler.op_num_upper_bound()
} else { None };
let to = op_num_upper_bound.unwrap_or(last_wal_index);

// :764-771 — the queue is bounded and must hold every pending op:
let update_queue_size = self.update_sender.load().capacity();
let to = cmp::max(to, last_wal_index.saturating_sub(update_queue_size as u64 - 1));
let to = cmp::min(to, last_wal_index);

// :783-789 — clamp: persisted applied_seq can legitimately lag first_index
// (saved every APPLIED_SEQ_SAVE_INTERVAL from a counter that restarts at zero
// on every process start; synchronous replay never feeds it)
let to = cmp::max(to, from);

// :838-852 — dead vector names: seed from config, grow on CreateVectorName,
// strip before applying or validation fails and the whole op drops
if let Some(name) = update.operation.created_vector_name() {
    valid_vector_names.insert(name.clone());
}
update.operation.retain_vector_names(&valid_vector_names);

// :866-890 — error policy: ServiceError/OutOfMemory abort load; NotFound warn;
// other errors log-and-continue
match &CollectionUpdater::update(&self.segments, op_num, update.operation, ...) {
    Err(err @ CollectionError::ServiceError { .. }) => return Err(err.clone()),
    Err(err @ CollectionError::OutOfMemory { .. }) => return Err(err.clone()),
    Err(err @ CollectionError::NotFound { .. }) => log::warn!("{err}"),
    Err(err) => log::error!("{err}"),
    Ok(_) => (),
}

// :930-934 — force flush after replay for on-disk consistency
segments.flush_all(FlushMode::Sync, true)?;

// :948-1000 — tail enqueue: clock tags advanced HERE (the worker discards them
// on re-read); unreadable entry logged+skipped but its op_num still enqueued
for entry in wal.read_range(to..last_wal_index) { ... newest_clocks.advance_clock(...) }
```

**Flow:** shard load opens the WAL → compute the replay window: default is the WHOLE remaining WAL synchronously (every read path assumes acknowledged ops are applied when load returns); under `prevent_unoptimized`, stop at the applied-seq upper bound and route the genuinely-unapplied tail through the update worker — because the worker signals optimizers per op and optimization is the only thing that makes deferred points visible → clamp the window against truncation and queue capacity → re-apply each entry with dead vector names stripped and a per-error-type policy → flush everything → enqueue any tail, advancing clock tags on the recovery side.
**Invariant:** (1) without prevent_unoptimized, NOTHING is deferred: all acknowledged points are visible the moment load returns and the update queue is empty; (2) the tail can never exceed the update queue capacity (asserted); (3) `to` is clamped to ≥ `from` so a stale applied_seq targeting already-truncated entries cannot fail the load; (4) ServiceError/OOM abort shard load (a corrupt state must not serve), while NotFound and other per-op failures are tolerated so one bad record does not crash-loop the node; (5) clock tags of queued tail entries are advanced at recovery time or the recovery point regresses across restarts and clock ticks get reused; (6) the WAL's first op number is never zero — `insert_fake_operation` appends an empty upsert at build time.
**Probe:** `lib/collection/src/tests/wal_recovery_test.rs::test_wal_replay_is_synchronous_without_prevent_unoptimized` (:623-741, read at pin): 500 wait-visible ops, applied_seq forced 100 below the head, reload ⇒ `points_count == 500` immediately and `pending_updates == 0`. Companion `test_wal_replay_truncated_past_applied_seq` (:891-1025): WAL acked past the applied-seq bound ⇒ load succeeds via the clamp, all 500 points present after the worker drains. Also read: `test_wal_replay_tolerates_corrupt_tail_entry` (:750-890, corrupt tail entry must not fail load) and `test_wal_replay_loads_pending_to_queue` (:454-610).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "load_from_wal replay WAL entries applied_seq prevent_unoptimized update queue", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the window algebra: synchronous replay covers everything except a tail that is (a) gated behind a config flag whose purpose is exactly "background apply is acceptable" and (b) capped by the apply queue's capacity, clamped against the truncated prefix. Adopt the split error policy (abort on service/OOM, tolerate per-op misses) and the post-replay forced flush. Adapt the applied-seq persistence cadence to your host; keep the "persisted waterline may lag the truncated prefix" clamp regardless. Omit the fake first operation if your WAL numbering tolerates zero. Caveat: the tail-routing flag doubles as the deferred-points visibility gate — do not decouple it from that gate without re-deriving why.
