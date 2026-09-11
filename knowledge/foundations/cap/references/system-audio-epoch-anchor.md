<!-- capsule-v2 -->
# system-audio-epoch-anchor — Where do you anchor a track whose first packet timing is meaningless (intermittent sources like WASAPI loopback)?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** Why does system audio anchor at the pipeline epoch instead of its first frame, and what breaks if you port it like the mic?

## Intermittent sources anchor at PipelineEpoch — a late first sound must never become the timeline's start
**Path/Symbol:** `crates/recording/src/studio_recording.rs:1674-1703` (`create_segment_pipeline` system-audio branch, both muxer variants); anchor type `AudioAnchor::PipelineEpoch` from `output_pipeline`.
**Signature:** `.with_audio_source::<screen_capture::SystemAudioSource>(system_audio_source).with_timestamps(start_time).with_audio_anchor(AudioAnchor::PipelineEpoch)`.
**Data Shape:** Two anchor modes: default (first-frame-derived, used by mic) vs `PipelineEpoch` (recording-start epoch).

### Decisive source
```rust
// System audio is intermittent (WASAPI loopback only delivers while
// sound plays), so its first packet is not a "source ready" marker:
// anchor the track at the recording epoch. This keeps a late first
// sound from becoming the latest start_time and cutting the head off
// the display/mic/camera tracks at playback.
```

**Flow:** Mic pipelines are built WITHOUT an explicit anchor (first timestamp = source ready). System-audio pipelines always pass `AudioAnchor::PipelineEpoch` for BOTH fragmented (m4a) and ogg outputs. At stop time the persisted sys start_time still participates in cross-track snapping (`snap_nearby_start_time`), but its raw first-packet time never defines the anchor.
**Invariant:** Track anchoring policy must match source DELIVERY semantics: continuous sources may use first-frame; intermittent sources must use epoch. Porting first-frame anchoring onto loopback audio shifts every later sound and can trim other tracks' heads when the editor takes max(start_times).
**Probe:** deterministic pins: `grep -c 'AudioAnchor::PipelineEpoch' crates/recording/src/studio_recording.rs` (2 — fragmented + ogg branches); `grep -n 'with_audio_anchor' crates/recording/src/studio_recording.rs`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "AudioAnchor PipelineEpoch system_audio", limit: 10 });
```

## Verdict
Adopt the per-source anchoring rule. Adapt the enum to your pipeline plumbing; keep the rationale comment.
