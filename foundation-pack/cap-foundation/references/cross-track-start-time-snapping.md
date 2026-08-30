<!-- capsule-v2 -->
# cross-track-start-time-snapping — How do you align per-track start times (display/mic/camera/system audio) so playback doesn't cut the head off a track?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** When two tracks start within noise of each other, when must their persisted start times be snapped together, and what is the snap threshold?

## Snap near-simultaneous starts to ONE reference time; threshold = one audio output frame
**Path/Symbol:** `crates/recording/src/studio_recording.rs:910-921` (`snap_nearby_start_time`), application ladder at `:967-1092` (`stop_recording`), threshold at `:935` (`CROSS_TRACK_SNAP_SECS = AUDIO_OUTPUT_FRAMES / DEFAULT_SAMPLE_RATE`).
**Signature:** `fn snap_nearby_start_time(raw_start: f64, reference_start: Option<f64>, threshold_secs: f64) -> f64`.
**Data Shape:** Start times are f64 seconds relative to the segment pipeline's start epoch (`timestamp.signed_duration_since_secs(s.pipeline.start_time)`); reference may be None (no snap).

### Decisive source
```rust
const CROSS_TRACK_SNAP_SECS: f64 = AUDIO_OUTPUT_FRAMES as f64 / DEFAULT_SAMPLE_RATE as f64;
// camera snaps to mic; display snaps to camera if present else mic;
// system audio snaps to mic, else to the already-snapped display start
```

**Flow:** Per finished segment, compute raw offsets of every track from the pipeline epoch. Camera → snap against mic. Display → snap against camera when present, else mic. System audio → snap against mic, else against the FINAL display value (post-snap). Each snap only fires when |raw − reference| ≤ threshold; far values are preserved verbatim.
**Invariant:** The snap threshold is DERIVED (one audio frame = 1024/48000 ≈ 21ms), not a magic constant — it captures "these tracks were started by the same spawn" while never swallowing genuine staggered starts. Snapping is transitive-by-chain in a fixed precedence order; porting with a different order changes which track owns the canonical start. A direct test pins both directions: `snap_nearby_start_time_aligns_near_track_start` (0.02→0.0) and `snap_nearby_start_time_keeps_far_track_start` (0.2 stays).
**Probe:** `crates/recording/src/studio_recording.rs:1976-1984` — tests `snap_nearby_start_time_keeps_far_track_start` + `snap_nearby_start_time_aligns_near_track_start`; async `stop_recording_preserves_far_display_start_time` (:1987) proves display 0.2s vs mic 0.0 survives unsnapped into meta.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "snap_nearby_start_time CROSS_TRACK_SNAP_SECS", limit: 10 });
```

## Verdict
Adopt the derived-threshold snap and the fixed precedence chain (camera→mic, display→(camera|mic), system→(mic|display)). Adapt frame constants to your audio stack.
