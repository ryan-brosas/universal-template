<!-- capsule-v2 -->
# quality-tier-encoder-ladder — How do Compatibility/Balanced/Ultra quality tiers map to encoder settings and capture caps, and what degrades when a camera is active?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** What are the per-tier bpp/preset values, the camera-active capture caps, and the memory-based default tier rule?

## Ultra = high-bpp+Medium preset; Balanced = QUALITY_BPP+Ultrafast; Compatibility halves bpp AND caps capture size/fps when a camera rides along
**Path/Symbol:** `crates/recording/src/capture_pipeline.rs:87-220` (macOS `make_studio_mode_pipeline`), `:222-357` (Windows twin); caps `studio_recording.rs:50-68` (`COMPATIBILITY_CAMERA_ACTIVE_MAX_SCREEN_{WIDTH,HEIGHT} = 1600×1000`, `camera_active_max_capture_size`), fps clamp `:1501-1505` (`max_fps.min(24)` when compatibility+camera); defaults `crates/recording/src/defaults.rs`.
**Signature:** `fn camera_active_max_capture_size(quality: StudioQuality, camera_active: bool) -> Option<(u32,u32)>`; `fn default_studio_recording_quality() -> StudioQuality` (memory < 16 GiB ⇒ Compatibility).
**Data Shape:** bpp ladder: `ULTRA_BPP` / `QUALITY_BPP * 0.5` / `QUALITY_BPP`; preset: Medium vs Ultrafast; Windows non-fragmented adds bitrate multiplier ultra?0.3:0.15.

### Decisive source
```rust
let effective_max_fps = if compatibility_quality && camera_active { max_fps.min(24) } else { max_fps };
// macOS fragmented:
let bpp = if ultra { H264EncoderBuilder::ULTRA_BPP }
          else if compatibility { H264EncoderBuilder::QUALITY_BPP * 0.5 }
          else { H264EncoderBuilder::QUALITY_BPP };
let preset = if ultra { H264Preset::Medium } else { H264Preset::Ultrafast };
```

**Flow:** Builder collects options (`with_max_fps` clamps 1..=120). Per segment: camera-active + Compatibility shrinks the SCREEN capture to ≤1600×1000 and fps to ≤24 so a weak machine can carry both encodes; Balanced/Ultra leave both unbounded. OOP muxer selection falls back IN-PROCESS when `resolve_muxer_binary()` fails — recording preservation outranks crash isolation. Linux always segments at 2s with Ultrafast unless Ultra.
**Invariant:** The camera-active degradation must apply ONLY under Compatibility — tests pin all three tiers × camera on/off. OOP fallback direction is one-way: binary missing ⇒ in-process, never fail the recording.
**Probe:** `crates/recording/src/studio_recording.rs:2042-2069` — tests `camera_active_capture_size_leaves_non_compatibility_native`, `camera_active_capture_size_keeps_guardrail_for_compatibility`, `inactive_camera_capture_size_is_unbounded`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "StudioQuality make_studio_mode_pipeline ULTRA_BPP", limit: 10 });
```

## Verdict
Adopt the three-tier ladder, the conditional camera-active guardrail trio (size/fps/bpp), and one-way OOP fallback. Adapt codec constants to your encoder.
