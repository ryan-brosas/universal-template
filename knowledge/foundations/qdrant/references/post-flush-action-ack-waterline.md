<!-- capsule-v2 -->
# Post-flush action queue — how does optimizer cleanup run without letting the WAL acknowledge pass unflushed data?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** After a flush, which deferred actions (proxy teardown, drop_data) may run, in what order, and how is the WAL acknowledge capped while their file effects are pending?

## Waterline-gated, ready_at-ordered drain with ack pins
**Path/Symbol:** `lib/shard/src/segment_holder/mod.rs`: `register_post_flush_action` (:462), `pending_post_flush_ack_cap` (:507), `run_ready_post_flush_actions` (:542-606); caller `segment_holder/flush.rs` :139-141; waterline rationale comment :530-541.
**Signature:** `fn run_ready_post_flush_actions(&self, persisted_version: SeqNumberType) -> OperationResult<Option<SeqNumberType>>`; action = `{ready_at: u64, ack_pin: Option<SeqNumberType>, action: () -> Result<PostFlushOutcome>}` with outcomes `Done | Retry`.
**Data Shape:** queues: `post_flush_actions` (pending), `in_flight_ack_floor` (pins of running actions); both behind locks with FIXED order actions→floor.

### Decisive source
```rust
let waterline = match self.failed_operation.first() {
    Some(failed) => persisted_version.min(*failed),   // first failed op caps maturity
    None => persisted_version,
};
let (ready, keep) = std::mem::take(&mut *actions)
    .into_iter().partition(|action| action.ready_at <= waterline);
// Record the pins of the actions we are about to run while they are out of the queue ...
*self.in_flight_ack_floor.lock() = ready.iter().map(|action| action.ack_pin).min();
ready.sort_by_key(|action| action.ready_at);
let mut blocked = false;
ready.retain_mut(|action| {
    if blocked { return true; }
    match (action.action)() {
        Ok(PostFlushOutcome::Done)  => false,
        Ok(PostFlushOutcome::Retry) => { blocked = true; true }   // stop and re-queue the rest
        Err(err) => { first_error = Some(err); blocked = true; false } // hard failure: dropped
    }
});
{ // Re-queue survivors and clear the in-flight floor together under the actions lock ...
    let mut actions = self.post_flush_actions.lock();
    actions.extend(ready);
    *self.in_flight_ack_floor.lock() = None;
}
```

**Flow:** flush completes → persisted version computed → waterline = min(persisted, first-failed-op) → partition queued actions by `ready_at <= waterline` → pin their min ack under the actions lock → run strictly in `ready_at` order (a proxy keeps its shared write segment alive until its successor takes ownership; drop_data needs sole ownership) → Done removes, Retry blocks-and-requeues the tail keeping pins live, Err drops the action and surfaces the error but still requeues everything after it → survivors re-added and floor cleared atomically → returned cap feeds the WAL acknowledge so it can never advance past data whose files contradict memory.
**Invariant:** (1) ordering by ready_at is a DEPENDENCY order, not just fairness — later actions consume resources released by earlier ones; once one blocks, ALL later ones re-queue even if individually runnable; (2) ack pins of in-flight actions must be recorded before running and cleared only after re-queueing, under consistent lock order (actions then floor), else the acknowledge can dip or race past unflushed files; (3) hard failures DROP their action (data is being destroyed; retry impossible) while Retry keeps it; (4) a fresh appendable segment reports persistent_version 0 until first flush, dragging the waterline near zero and deferring actions — known, documented trade-off.
**Probe:** `grep -c "test_post_flush_action" lib/shard/src/segment_holder/tests.rs` → prints `3`. Direct tests: `test_post_flush_action_retry_keeps_ack_pin` (:2041 area, asserts version==ACK_PIN across retries then WATERLINE after completion), `test_post_flush_action_in_flight_pin_stays_visible`, `test_post_flush_action_hard_failure_is_dropped`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "run_ready_post_flush_actions register_post_flush_action pending_post_flush_ack_cap in_flight_ack_floor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt waterline capping, dependency-ordered drain, block-propagation on Retry, drop-on-Err semantics, and the two-lock ack-pin protocol. Adapt lock primitives. Omit proxy-segment specifics if not porting shard optimization.
