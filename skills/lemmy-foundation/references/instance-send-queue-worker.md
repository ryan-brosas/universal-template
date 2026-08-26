<!-- capsule-v2 -->
# Instance send-queue worker — how do you deliver every activity to one remote peer exactly-once in-order without a broker?

**Source:** lemmy AGPL-3.0 `main@439734dd638a2c06a2f907beab7dcf4646e88f86`; Codebase Memory `ext-lemmy`. **Question:** How does one per-instance worker turn a global monotone `sent_activity` table into a strictly ordered, crash-resumable delivery stream to a single remote domain?

## InstanceWorker loop
**Path/Symbol:** `crates/apub/send/src/worker.rs:InstanceWorker` (`loop_until_stopped` :120–199, `handle_send_results` :249–294, `pop_successfuls_and_write` :317–352, `spawn_send_if_needed` :357–429).
**Signature:** `init_and_loop(instance: Instance, config: FederationConfig<LemmyContext>, federation_worker_config: FederationWorkerConfig, stop: CancellationToken, stats_sender: UnboundedSender<FederationQueueStateWithDomain>) -> LemmyResult<()>`.
**Data Shape:** persisted state row `FederationQueueState { instance_id, last_successful_id: Option<ActivityId>, last_successful_published_time_at, fail_count: i32, last_retry_at: Option<DateTime> }`; in-memory `successfuls: BinaryHeap<SendSuccessInfo>` (min-heap via reversed `Ord`, :39–48), `in_flight: i8`; consts `MAX_SUCCESSFULS = 1000` (:43), `SAVE_STATE_EVERY_TIME = 60s` prod / 0 test (:37–41), `MIN_ACTIVITY_SEND_RESULTS_TO_HANDLE = 4` prod (:47).

### Decisive source
```rust
// worker.rs:129 — the wait predicate: block on results only if (last request failed AND something
// is still in flight) OR too many buffered successes OR at the concurrency ceiling
let need_wait_for_event = (self.in_flight != 0 && self.state.fail_count > 0)
  || self.successfuls.len() >= MAX_SUCCESSFULS
  || self.in_flight >= self.federation_worker_config.concurrent_sends_per_instance;

// worker.rs:145-153 — sanity check tying the cursor together; any drift = hard error, no silent skip
let next_id_to_send = ActivityId(last_sent_id.0 + 1);
let expected_next_id = self.state.last_successful_id.map(|id|
  id.0 + successfuls_len + i64::from(self.in_flight) + 1);
if expected_next_id != Some(next_id_to_send.0) {
  return Err(anyhow::anyhow!("{}: next id to send is not as expected: {:?} != {:?}", ...));
}

// worker.rs:332-345 — commit the contiguous prefix only; out-of-order successes stay heap-buffered
while self.successfuls.peek()
  .map(|a| a.activity_id == ActivityId(last_id.0 + 1)).unwrap_or(false) {
  let next = self.successfuls.pop().context("peek above ensures pop has value")?;
  last_id = next.activity_id;
  self.state.last_successful_id = Some(next.activity_id);
}
```

**Flow:** load state from DB → first-seen instances initialize `last_successful_id = max(sent_activity.id)` so history is never backfilled (`get_last_sent_id` :230–247, writes immediately so a crash can't re-read it as 0) → loop: drain result events → pop contiguous success prefix into `last_successful_id` → persist state when forced by failure or every 60 s → claim next id `(last_sent + 1)` and verify the cursor identity → fetch activity (`get_activity_cached`) → collect inbox URLs → empty ⇒ synthetic skipped Success, else spawn `SendRetryTask` → on shutdown save state once more (:197). Skips report `was_skipped: true` and deliberately do NOT decrement `fail_count` or touch instance-alive timestamps (:270–273).
**Invariant:** the DB cursor only ever advances over a gapless prefix of activity ids — a hole would silently drop that activity forever, because resume restarts at `last_successful_id + 1`. Concurrent sends reorder arrivals; the min-heap plus prefix-pop repairs the order before anything durable is written.
**Probe:** `crates/apub/send/src/worker.rs` tests `test_send_40` (:617–635), `test_send_15_20_30` (:643–665) — batches of activities all arrive at a live local HTTP inbox (`listen_activities` :733) with bodies byte-equal to the stored activity JSON.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lemmy", name_pattern: "loop_until_stopped", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the DB-as-queue cursor protocol (monotone ids + persisted high-water mark + prefix-only commit + out-of-order success buffer), the fail-gated concurrency ladder, first-seen cursor initialization, and the internal-error-becomes-skip escape hatch that keeps one poisoned activity from stalling a whole peer queue. Adapt the concrete channel types and the 60 s state-save cadence to your host's shutdown/crash model. Omit Lemmy-specific inbox collection details (see the community-inbox capsule) and the stats side-channel.
