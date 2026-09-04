<!-- capsule-v2 -->
# studio-recording-actor-fsm — How do you model pause/resume/stop for a multi-track screen recording without losing segment state or cursor identity?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** What are the legal actor states, the message set, and the state-transition invariants (segment indices, cursor id continuity) a porter must reproduce?

## kameo actor: Recording ⇄ Paused → Stopped via take-state handlers
**Path/Symbol:** `crates/recording/src/studio_recording.rs:71-84` (`enum ActorState`), messages at `:169-345` (`Stop`/`Pause`/`Resume`/`Cancel`/`SetMicFeed`/`SetCameraFeed`/`IsPaused`), spawn at `:819-902` (`spawn_studio_recording_actor`).
**Signature:** `enum ActorState { Recording { pipeline: Pipeline, index: u32, segment_start_time: f64, segment_start_instant: Instant }, Paused { next_index: u32, cursors: Cursors, next_cursor_id: u32 } }`; `async fn handle(&mut self, msg, ctx) -> anyhow::Result<T>`.
**Data Shape:** Actor owns `recording_dir`, `Option<ActorState>` (`None` = terminal/stopped), `SegmentPipelineFactory`, `Vec<RecordingSegment>`, a `watch::Sender<Option<Result<(), PipelineDoneError>>>` completion channel, and a display notch resolved ONCE at start.

### Decisive source
```rust
impl Message<Pause> for Actor {
    async fn handle(&mut self, _: Pause, _: &mut Context<Self, Self::Reply>) -> Self::Reply {
        self.state = match self.state.take() {
            Some(ActorState::Recording { pipeline, segment_start_time, index, .. }) => {
                let (cursors, next_cursor_id) = self
                    .stop_pipeline(pipeline, segment_start_time).await
                    .context("stop_pipeline")?;
                Some(ActorState::Paused { next_index: index + 1, cursors, next_cursor_id })
            }
            state => state,
        };
        Ok(())
    }
}
```

**Flow:** spawn creates the FIRST pipeline immediately (`create_next(Default::default(), 0)`), writes an InProgress meta when fragmented, and enters `Recording{index:0}`. Every handler does `self.state.take()` first — the match arms consume the old state and produce the new one, so illegal transitions fall through to `state => state` (no-op) rather than corrupting. Pause stops the live pipeline, pushes the finished `RecordingSegment` onto the vec, and carries `cursors` + `next_cursor_id` + bumped `index` into Paused. Resume calls `segment_factory.create_next(cursors, next_cursor_id)` so the new segment continues cursor ids across the gap. Stop sleeps until `segment_start_instant + 1s` (minimum segment duration) before stopping, then runs finalization. SetMicFeed/SetCameraFeed are only legal while Paused ("Pause the recording before changing microphone input"); device ids for each segment are snapshotted from the factory at stop time.
**Invariant:** Segment index continuity lives in the STATE, not the factory's internal counter alone — pause must carry `index+1` forward; cursor identity (`next_cursor_id`) must round-trip through every pause/resume cycle or cursors after the pause get re-id'd and the editor mis-renders them.
**Probe:** `crates/recording/tests/sync_matrix.rs` + unit tests in-file; deterministic pin: `grep -n 'next_index: index + 1' crates/recording/src/studio_recording.rs` (1 hit).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "studio recording ActorState Pause Resume", limit: 10 });
```

## Verdict
Adopt the take-state FSM shape, the minimum-segment-duration stop guard, and mid-pause device swap gating. Adapt the kameo actor framework to your host's actor/channel system. Omit macOS-specific SendableShareableContent plumbing.
