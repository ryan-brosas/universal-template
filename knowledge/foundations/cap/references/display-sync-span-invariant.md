<!-- capsule-v2 -->
# display-sync-span-invariant — How do you detect the class of bug where a finalized video's container is shorter than the timestamps you actually muxed?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** What cross-check runs at both record-stop and recovery time, and why are short and long container mismatches treated asymmetrically?

## Container SHORTER than the muxed timestamp span = desync bug (error); LONGER = legitimate VFR trailing hold (debug only)
**Path/Symbol:** `crates/recording/src/output_validation.rs:107-151` (`check_display_sync_span`, `SYNC_SPAN_TOLERANCE_SECS = 0.5`, `SYNC_SPAN_TOLERANCE_RATIO = 0.03`); called from `studio_recording.rs:1031-1043` and `recovery.rs:853-862` (expected duration re-read from `project-config.json` timeline).
**Signature:** `pub fn check_display_sync_span(display_path: &Path, expected: Duration) -> Option<f64>` — returns `Some(shortfall)` when violated, None when consistent or unprobeable.
**Data Shape:** Expected = media span persisted by the recorder (`(last-first)+1/fps`); actual = container duration via `get_media_duration`. Tolerance = `max(expected × 3%, 0.5s)`.

### Decisive source
```rust
/// The two are produced independently: the expected duration comes from the
/// pipeline's timestamp span, the container duration from what the encoder
/// and muxer wrote. A container SHORTER than the span means timestamps were
/// mangled between the pipeline and the file — the class of bug that
/// silently desyncs audio/video. A LONGER container is legitimate for VFR
/// content: muxers extend the final frame through any trailing static-screen
/// hold ... Non-fatal: logs a structured warning and returns the mismatch.
if shortfall > tolerance {
    tracing::error!(..., "SYNC INVARIANT VIOLATION: display track duration is shorter than \
         the muxed timestamp span; this recording may have desynced audio/video");
    Some(shortfall)
} else { debug!(...); None }
```

**Flow:** At stop: non-fragmented `.mp4` outputs get checked immediately against the just-computed span. In recovery: after remuxing fragments to `display.mp4`, the expected duration is RE-DERIVED from what the recorder earlier persisted into `project-config.json` (`timeline.segments[].recordingSegment == index → end − start`) — so the check validates remux fidelity against pre-crash intent. Failure logs an error-level structured event but never aborts finalization.
**Invariant:** Asymmetry is the point: short = timestamps mangled (must be loud), long = trailing keyframe padding/AVFoundation session end (benign). The check must be non-fatal — a diagnostics warning must not destroy a recoverable recording.
**Probe:** deterministic pin: `grep -c 'check_display_sync_span' crates/recording/src/studio_recording.rs crates/recording/src/recovery.rs` (1 each). Direct behavioral coverage rides `recover_after_simulated_crash_produces_playable_mp4_with_preserved_duration` in `crates/recording/tests/recovery.rs`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "check_display_sync_span SYNC_SPAN_TOLERANCE", limit: 10 });
```

## Verdict
Adopt the asymmetric duration cross-check and its dual call sites (stop + post-recovery-from-config). Adapt probe functions; keep it non-fatal.
