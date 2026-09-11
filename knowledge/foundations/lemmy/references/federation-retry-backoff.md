<!-- capsule-v2 -->
# Federation retry backoff — what is the failure-count protocol that stops one dead peer from melting the queue?

**Source:** lemmy AGPL-3.0 `main@439734dd638a2c06a2f907beab7dcf4646e88f86`; Codebase Memory `ext-lemmy`. **Question:** How do concurrent send tasks share one backoff counter so N simultaneous failures count as ONE failure step, and how is the sleep resumed after a crash?

## federate_retry_sleep_duration
**Path/Symbol:** `crates/utils/src/lib.rs:federate_retry_sleep_duration` (:131–140); consumers `crates/apub/send/src/send.rs:SendRetryTask.send_retry_loop` (:99–157) and `crates/apub/send/src/worker.rs:initial_fail_sleep` (:201–226).
**Signature:** `pub fn federate_retry_sleep_duration(retry_count: i32) -> Duration`; task-side `send_retry_loop(self) -> Result<()>` where `Ok` means "succeeded or worker cancelled" and errors are internal-only.
**Data Shape:** `fail_count: i32` persisted in `FederationQueueState` next to `last_retry_at: Option<DateTime<Utc>>`; the task receives an immutable `initial_fail_count: i32` snapshot at spawn (worker.rs :390).

### Decisive source
```rust
// crates/utils/src/lib.rs:131 — 1.25^n seconds, first error FREE, capped at one day
if retry_count == 1 { return Duration::from_secs(0); }        // first failure = immediate retry
let retry_count = retry_count - 1;
let pow = 1.25_f64.powf(retry_count.into());
let pow = Duration::try_from_secs_f64(pow).unwrap_or(DAY);     // overflow → DAY, never panic
min(DAY, pow)

// send.rs:126-148 — per-request ladder; each failure reports the NEW count then sleeps it
let mut fail_count = initial_fail_count;
while let Err(e) = task.sign_and_send(&context).await {
  fail_count += 1;
  report.send(SendActivityResult::Failure { fail_count })?;
  let retry_delay = federate_retry_sleep_duration(fail_count);
  tokio::select! {
    () = sleep(retry_delay) => {},
    () = stop.cancelled() => return Ok(()),   // cancelled sends report NOTHING — worker must not hang
  }
}

// worker.rs:276-288 — max-wins override: failures inside one sleep window collapse to a single step
SendActivityResult::Failure { fail_count, .. } => {
  if fail_count > self.state.fail_count {      // "Any amount of failures within a fail-sleep period
    self.state.fail_count = fail_count;        //  should only count as one failure"
    self.state.last_retry_at = Some(Utc::now());
    force_write = true;
  }
}
```

**Flow:** request fails → task increments its local copy, reports `{fail_count}`, sleeps `1.25^(n-1)` s (0 for n=1) → worker keeps only the max reported count and stamps `last_retry_at`, forcing a state write → on success (`was_skipped == false`) the worker decrements `fail_count` toward 0 (`max(0, fc − 1)`, worker.rs :271) and marks the instance alive → queue restart sleeps only the REMAINING backoff: `required − elapsed` via `checked_sub` (worker.rs :208–212), so a SIGKILL mid-backoff resumes rather than restarting the ladder.
**Invariant:** the shared counter is monotone within a failure episode (never re-derived from concurrent losers — ten simultaneous 500s must not produce 2^10-second waits), and every long sleep is raced against `stop.cancelled()` so shutdown is immediate. Cancelled tasks exit WITHOUT reporting, which is why the result-drain selects on cancellation too (worker.rs :253–265 comment).
**Probe:** `crates/utils/src/lib.rs` test `test_federate_retry_sleep_duration` (:146–158) pins 1→0 s, 2→1.25 s, 5→2.441406250 s, 100→DAY; `crates/apub/send/src/worker.rs` test `test_errors` (:688–717) drives real HTTP 500s through the live loop and watches `fail_count` rise to 2–3 then return to 0.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lemmy", name_pattern: "federate_retry_sleep_duration", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the 1.25^n-with-free-first-retry curve, the day cap with overflow-to-cap (no panic), the max-wins collapse of concurrent failures into one step, decrement-on-success, and the remaining-duration resume across restarts. Adapt the base/duration constants and channel plumbing to your host. Omit the Lemmy stats printer formatting.
