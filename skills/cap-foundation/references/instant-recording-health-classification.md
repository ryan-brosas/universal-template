<!-- capsule-v2 -->
# instant-recording-health-classification — At stop time, how do you grade a recording Healthy/Degraded/Damaged from on-disk evidence alone, and how does drop-safety work for the instant actor?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** What disk evidence maps to which health state, and why does ActorHandle::Drop send Stop instead of cancelling?

## init+segments ⇒ Healthy; init-only ⇒ Degraded(too short); nothing ⇒ Damaged — and Drop always finalizes
**Path/Symbol:** `crates/recording/src/instant_recording.rs:102-217` (`impl Drop for ActorHandle`, `Actor::stop`, `Message<Stop>` health ladder); health type `lib.rs:156-172` (`RecordingHealth::is_uploadable`).
**Signature:** `let health = if has_segments || has_output_mp4 { Healthy } else if has_init { Degraded { issues: ["Recording too short — no complete segments produced"] } } else { Damaged { reason: "No video segments produced" } };`
**Data Shape:** Evidence read from `content/display/`: `init.mp4` existence; any `*.m4s`; non-empty `output.mp4` (metadata.len() > 0). `CompletedRecording { project_path, meta: InstantRecordingMeta::Complete{fps, sample_rate:None}, display_source, health }`.

### Decisive source
```rust
impl Drop for ActorHandle {
    fn drop(&mut self) {
        let actor_ref = self.actor_ref.clone();
        tokio::spawn(async move {
            let _ = actor_ref.tell(Stop).await;   // finalize, never cancel
        });
    }
}
```

**Flow:** Stop first folds any open pause interval into `total_pause_duration` (pause_started_at → elapsed), then stops audio+video concurrently (`tokio::join!`) with video errors fatal and audio errors only warned. Health is classified from disk AFTER the muxer finishes. `is_uploadable()` accepts Healthy | Repaired | Degraded — Damaged blocks upload.
**Invariant:** Dropping a live recorder must STOP (finalize + remux what exists), not cancel — an accidental handle drop mid-recording preserves user data. Pause accounting must close any open interval at stop or durations drift long by the pause length. Read-dir failure is treated as "no segments" with a warning, not a panic.
**Probe:** deterministic pins: `grep -n 'impl Drop for ActorHandle' crates/recording/src/instant_recording.rs` (1); `grep -c 'has_segments' crates/recording/src/instant_recording.rs`. Behavioral coverage: `crates/recording/tests/instant_mode_scenarios.rs`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "instant recording RecordingHealth ActorHandle Drop", limit: 10 });
```

## Verdict
Adopt the evidence-based health ladder and stop-on-Drop semantics. Adapt to your actor runtime; keep audio-stop failures non-fatal relative to video.
