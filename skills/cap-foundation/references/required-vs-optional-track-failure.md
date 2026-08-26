<!-- capsule-v2 -->
# required-vs-optional-track-failure — When one recording track (mic/camera/system audio) dies mid-recording, how do you keep the display track and finish the recording?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** What is the exact required-vs-optional failure semantics across runtime AND stop phases, and how are failures recorded exactly once?

## Display is the only REQUIRED track; every other failure is a recorded, non-fatal degradation
**Path/Symbol:** `crates/recording/src/studio_recording.rs:383-522` (`RecordingTrackKind`, `TrackFailureStage`, `TrackFailureRecord`, helpers), watcher at `:567-648` (`Pipeline::spawn_watcher`), stop fan-out at `:524-565` (`Pipeline::stop`).
**Signature:** `fn record_track_failure(&SharedTrackFailures, track: RecordingTrackKind, stage: TrackFailureStage /*Runtime|Stop*/, error: impl Into<String>)`; `fn finalize_optional_track(track, result: Result<Option<FinishedOutputPipeline>, anyhow::Error>, failures) -> Option<FinishedOutputPipeline>`.
**Data Shape:** `SharedTrackFailures = Arc<Mutex<Vec<TrackFailureRecord>>>`; each record `{track, stage, error}`; diagnostics sidecar aggregates per-segment into `recording-diagnostics.json` (`version: 1`, segments with index/start/end/track_failures).

### Decisive source
```rust
// spawn_watcher: per-track done_fut raced in a FuturesUnordered
while let Some((track, required, res)) = futures.next().await {
    if let Err(err) = res {
        if required {
            if completion_tx.borrow().is_none() {
                let _ = completion_tx.send(Some(Err(err)));
            }
        } else {
            warn!(?track, error = %err, "Optional recording track failed during runtime");
            record_track_failure(&track_failures, track, TrackFailureStage::Runtime, err.to_string());
        }
    }
}
```

**Flow:** Only Display is pushed as `required=true`; mic/camera/system-audio done-futures carry `required=false`. A required failure publishes `Some(Err)` on the completion watch channel ONCE (guarded by `is_none()`); optional failures only append to the shared ledger. At stop, `futures::join!` stops the three optional tracks concurrently while the screen stops after; each optional result goes through `finalize_optional_track`, which converts a stop-phase error into a ledger record (skipping the write when the same track ALREADY has a runtime failure — no duplicates) and returns None. Poisoned mutexes are recovered via `poisoned.into_inner()` everywhere — a panic in one writer must not lose the ledger.
**Invariant:** An optional track's failure NEVER aborts or fails the recording; it degrades it and lands in the diagnostics sidecar. A 4xx-style definitive rejection arriving AFTER any transient failure during completion must surface as uncertain, not clean-error (mirror of uploader rule). Ledger writes are idempotent per (track, phase).
**Probe:** `crates/recording/src/studio_recording.rs:2072-2131` — unit tests `finalize_optional_track_records_stop_failure`, `finalize_optional_track_does_not_duplicate_runtime_failure`, plus async test `stop_preserves_display_when_optional_track_fails_during_runtime` (:2243). Deterministic pin: `grep -c 'finalize_optional_track' crates/recording/src/studio_recording.rs` (≥4).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "track failure RecordingTrackKind finalize_optional_track", limit: 10 });
```

## Verdict
Adopt the required-display + optional-peripherals failure model, the exactly-once ledger, and the non-fatal diagnostics JSON. Adapt track names to your pipeline. Omit the concrete muxer types.
