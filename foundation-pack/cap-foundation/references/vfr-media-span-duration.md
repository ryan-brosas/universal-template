<!-- capsule-v2 -->
# vfr-media-span-duration — What duration do you persist for a variable-frame-rate display track so static screens don't shorten the recording?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** frame_count/fps, wall-clock span, or timestamp span — which is the correct persisted duration for VFR screen capture, and what fallbacks apply?

## Persist the ENCODED MEDIA SPAN (last − first muxed timestamp + one nominal frame), never wall-clock or frame_count/fps
**Path/Symbol:** `crates/recording/src/studio_recording.rs:1000-1026` (`display_media_duration` in `stop_recording`).
**Signature:** `match s.pipeline.screen.video_timestamp_span { Some((first,last)) if fps>0 => (last-first).as_secs_f64() + 1.0/fps, _ => video_frame_count as f64 / f64::from(fps) }`.
**Data Shape:** `FinishedOutputPipeline` carries `video_info: Option<VideoInfo>` (fps source), `video_frame_count: u64`, `video_timestamp_span: Option<(Timestamp, Timestamp)>`; default fps 30 when info missing.

### Decisive source
```rust
// Use the encoded display-media span (first to last muxed timestamp plus one
// nominal frame), not the wall-clock recording span which includes
// pipeline-drain latency, and not frame_count / fps, which under-reports VFR
// content by the length of every capture gap (static screens, dropped frames).
let display_media_duration = match s.pipeline.screen.video_timestamp_span {
    Some((first, last)) if display_fps > 0 => {
        (last - first).as_secs_f64() + 1.0 / f64::from(display_fps)
    }
    _ if display_fps > 0 => { s.pipeline.screen.video_frame_count as f64 / f64::from(display_fps) }
    _ => 0.0,
};
```

**Flow:** Preferred = timestamp span + one frame (covers trailing static hold). Fallback = frame_count/fps only when no span was recorded. Zero when neither exists → such segments are filtered OUT of the timeline (`(segment.duration > 0.0).then_some(...)` at :1116). The same duration feeds a container cross-check via `output_validation::check_display_sync_span` for non-fragmented mp4s.
**Invariant:** The persisted duration IS the timeline the editor uses for unedited recordings — using wall-clock adds drain latency; using frame_count/fps silently truncates every capture gap. Timeline segments with duration ≤ 0 must be dropped, not written.
**Probe:** deterministic pin: `grep -n 'video_timestamp_span' crates/recording/src/studio_recording.rs | head -3` (≥2 hits: struct field + match); sync-span counterpart test in `crates/recording/src/output_validation.rs:127`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "video_timestamp_span display_media_duration", limit: 10 });
```

## Verdict
Adopt the media-span-plus-one-frame rule and its two-step fallback ladder. Adapt VideoInfo plumbing to your encoder metadata.
