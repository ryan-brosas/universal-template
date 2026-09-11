<!-- capsule-v2 -->
# WAL-backed update worker loop — how does an applied-operation waterline stay correct when clients may or may not wait?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** After an update is WAL-appended, who applies it, when is the WAL flushed relative to apply, and how is the "applied up to" watermark advanced without blocking the queue on slow clients?

## Single-worker apply with flush-before-apply and detached deferred waits
**Path/Symbol:** `lib/collection/src/update_workers/update_worker.rs`: `update_worker_fn` (:44-228), `update_worker_internal` (:305-357); caller context `lib/collection/src/shards/local_shard/shard_ops.rs`: `submit_update` (:61-83), `LocalShard::update` (:235-252).
**Signature:** `pub async fn update_worker_fn(collection_name: CollectionId, receiver: Receiver<UpdateSignal>, optimize_sender: Sender<OptimizerSignal>, wal: LockedWal, segments: LockedSegmentHolder, update_operation_lock: Arc<tokio::sync::RwLock<()>>, update_tracker: UpdateTracker, prevent_unoptimized: bool, optimization_finished_receiver: watch::Receiver<()>, applied_seq_handler: Arc<AppliedSeqHandler>, cancel: CancellationToken) -> Receiver<UpdateSignal>`.
**Data Shape:** signals are `UpdateSignal::Operation(OperationData { op_num, operation: Option<Box<...>>, sender: Option<FeedbackSender>, wait_for_deferred, hw_measurements })`; a `None` operation means "re-read from WAL".

### Decisive source
```rust
// :52-58 — cancellation is checked FIRST (biased select)
let signal = tokio::select! {
    biased;
    _ = cancel.cancelled() => { break receiver; }
    signal = receiver.recv() => match signal { ... }
};

// :80-96 — fallback path: operation body re-read from WAL
let record = tokio::task::spawn_blocking(move ||
    wal_clone.blocking_lock().read_raw_record(op_num)).await ...;

// :305-315 (update_worker_internal) — flush BEFORE apply when anyone waits
if wait {
    wal.blocking_lock().flush().map_err(|err| ...)?;
}
// :330-337 — apply under the shared update lock
CollectionUpdater::update(&segments, op_num, operation,
    update_operation_lock.clone(), update_tracker.clone(), &...)

// :185-189 — waterline advances only after success...
if let Err(err) = applied_seq_handler.update(op_num) { log::error!(...) }
// :190-217 — deferred wait DETACHED per client so the queue keeps draining
if wait_for_deferred && prevent_unoptimized {
    if let Some(mut feedback) = sender {
        tokio::spawn(async move { /* wait_for_deferred_points_ready then send_feedback */ });
    }
} else {
    send_feedback(sender, Ok(InternalUpdateResult { op_num, status: UpdateStatus::Completed }), op_num);
}
```

**Flow:** submit side (`submit_update`) resolves filter/condition ops to concrete point ids BEFORE the WAL (replicas resolve identically), checks WAL disk space, takes `update_lock.read()` across append+dispatch → worker receives one signal at a time → optional WAL re-read → spawn_blocking apply: explicit WAL flush first iff any client waits (durability before acknowledgement), then `CollectionUpdater::update` under `update_operation_lock` (which also serializes against search-time segment swaps that need exclusive access) → success notifies optimizers via `OptimizerSignal::Operation(op_num)` and advances `applied_seq_handler`; failure feeds back the error WITHOUT advancing the waterline → waiting clients get feedback; deferred-point waits (`prevent_unoptimized`) detach into a spawned task so only the originating client blocks. `LocalShard.update` stays cancel-safe because nothing is appended or dispatched until its single WAL write.
**Invariant:** (1) the applied-sequence watermark must never pass a failed op — later replays resume exactly there; (2) ack-before-flush inversion is forbidden: `wait == true` forces `wal.flush()` before apply so an acked point survives restart; (3) Nop/Stop signals forward to optimizers even when the process is dying (log-and-continue, never panic); (4) cancellation breaks the loop but the optimizer channel still receives `OptimizerSignal::Stop`.
**Probe:** direct test `lib/collection/src/tests/deferred_points_tests.rs::test_wait_deferred_does_not_block_update_worker` (:153-237, read at pin): with optimizers disabled, a waiting client A in the deferred-wait branch must not block client B — without the detach, B's 5 s timeout trips. The flush-before-ack ordering is pinned by direct reads of :44-228/:305-357 (`wait` ⇒ `wal.flush()` before `CollectionUpdater::update`) plus the cancel-safety contract comment in `shard_ops.rs` :238-242. Recorded as runner-block evidence for live execution (see verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "update worker fn UpdateSignal Operation applied seq handler optimizer signal deferred points", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-applier loop: flush-before-ack for waiting clients, success-only watermark advance, detached per-client deferred waits, biased cancellation. Adapt `spawn_blocking` boundaries and the optimizer signal bus to your async runtime. Omit qdrant's clock-tag replica plumbing carried inside `OperationWithClockTag`.
