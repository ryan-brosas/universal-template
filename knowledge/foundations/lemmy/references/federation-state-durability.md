<!-- capsule-v2 -->
# Federation queue state durability — what exactly survives a crash so no activity is lost or duplicated?

**Source:** lemmy AGPL-3.0 `main@439734dd638a2c06a2f907beab7dcf4646e88f86`; Codebase Memory `ext-lemmy`. **Question:** How often is queue progress persisted, what forces an early write, and why is at-least-once re-delivery the accepted failure mode?

## save_and_send_state cadence
**Path/Symbol:** `crates/apub/send/src/worker.rs` — `save_and_send_state` (:431–442), force-write sites `handle_send_results` (:249–294, `force_write = true` on any Failure), cadence gate `pop_successfuls_and_write` (:347–351), shutdown final write (`loop_until_stopped` :196–198), first-seen immediate persist (`get_last_sent_id` :230–247).
**Signature:** `FederationQueueState::upsert(&mut self.pool, &self.state)`; stats mirror `stats_sender.send(FederationQueueStateWithDomain { state: clone, domain })`.
**Data Shape:** one row per instance: `{ instance_id (PK), last_successful_id: Option<ActivityId>, last_successful_published_time_at: Option<DateTime>, fail_count: i32, last_retry_at: Option<DateTime> }`; `SAVE_STATE_EVERY_TIME = 60 s` prod / 0 in tests (`#[cfg(test)]` twin statics :37–41); `last_state_insert: DateTime<Utc>` in-memory watermark.

### Decisive source
```rust
// worker.rs:35-41 — the comment IS the design contract:
/// Save state to db after this time has passed since the last state (so if the server crashes
/// or is SIGKILLed, less than X seconds of activities are resent)
static SAVE_STATE_EVERY_TIME: Duration = Duration::from_secs(60);

// worker.rs:347-350 — time-based flush of the CURSOR, plus event-based flush on failure
let save_state_every = chrono::Duration::from_std(SAVE_STATE_EVERY_TIME)?;
if force_write || (Utc::now() - self.last_state_insert) > save_state_every {
  self.save_and_send_state().await?;
}

// worker.rs:196-198 — graceful shutdown flushes once more AFTER the loop exits
// final update of state in db on shutdown
self.save_and_send_state().await?;
```

**Flow:** cursor advances only via the prefix-pop (see instance-send-queue-worker capsule) → writes are batched to ≤1/minute under load BUT failures force an immediate write so retry bookkeeping (`fail_count`, `last_retry_at`) is crash-safe → cancellation path drains pending results then upserts a final state → on restart the worker resumes from `last_successful_id + 1`, re-sending everything not yet checkpointed.
**Invariant:** the protocol deliberately chooses AT-LEAST-ONCE delivery: anything sent-but-uncheckpointed within the 60 s window gets re-sent after a crash, and receivers must tolerate duplicates (inbound dedup table exists precisely for this — see shared-inbox-receive-gate capsule). Exactly-once would require transactional coupling between HTTP success and DB write, which is impossible across networks; the 60 s window bounds duplicate volume instead. The stats channel mirrors every persist for live observability without extra queries.
**Probe:** `crates/apub/send/src/worker.rs` test `test_stats` (:577–611) asserts a stats event arrives at startup, after each successful send, AND once more on shutdown (`rcv.state.last_successful_id == sent.id`, then channel-disconnect semantics).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lemmy", name_pattern: "FederationQueueState", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt bounded-staleness checkpointing with event-forced early writes (failure bookkeeping must be durable immediately), final-flush-on-shutdown, and explicit at-least-once semantics with a receiver-side dedup table as the counterpart. Adapt the window to your duplicate tolerance and transport cost. Omit the log-stats formatting plane.
