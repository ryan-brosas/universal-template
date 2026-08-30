---
name: cap-foundation
description: "Use when building a screen-recording pipeline: multi-track studio recording actor (pause/resume segmented), crash-safe fragmented MP4 recovery with manifest ladders, browser MediaRecorder spooling, streaming multipart upload with uncertain-completion semantics, getDisplayMedia retry ladders, and VFR-safe duration/sync invariants."
disable-model-invocation: true
---

# Cap Foundation

## Use this for
Use when porting a desktop-grade screen recorder (Rust capture→encode→mux pipelines with per-track failure isolation), designing crash-recovery for fragmented recordings (manifests, tmp rescue, respawn groups), building browser recording backends (IndexedDB spool liveness, local backup capping), streaming multipart uploads that must survive flaky networks, or wiring getDisplayMedia acquisition with graceful degradation. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/studio-recording-actor-fsm.md` — kameo actor FSM: Recording⇄Paused→Stopped via take-state handlers; segment index + cursor-id continuity across pauses; 1s minimum-segment stop guard.
- `references/required-vs-optional-track-failure.md` — display is the only required track; mic/camera/sys-audio failures at Runtime OR Stop land once in a poison-proof ledger and surface as `recording-diagnostics.json`, never abort.
- `references/cross-track-start-time-snapping.md` — snap near-simultaneous track starts to one reference within `AUDIO_OUTPUT_FRAMES/sample_rate`; fixed precedence chain camera→mic, display→(camera|mic), sys→(mic|display).
- `references/vfr-media-span-duration.md` — persist encoded media span (+1 nominal frame), not wall-clock or frame_count/fps; zero-duration segments drop from the timeline.
- `references/fragment-manifest-recovery-ladder.md` — manifest → size+decodability gates → m4s rescan → dir probe; status gate InProgress/NeedsRemux only; Failed is terminal.
- `references/tmp-rescue-and-respawn-groups.md` — promote complete-tail `.m4s.tmp`, refuse truncated with corrupt marker + health event, remux respawn groups separately then concatenate.
- `references/recovery-start-time-fallback.md` — recovered audio tracks inherit display start_time (editor offset stays 0); <500B audio files dropped.
- `references/display-sync-span-invariant.md` — asymmetric duration cross-check: container SHORTER than muxed span = desync bug (error), longer = benign VFR hold; runs at stop AND post-remux against project-config.
- `references/atomic-manifest-writes.md` — temp+fsync+rename+DIR-fsync recipe; InProgress meta written at start as recovery beacon; final-meta save failure stays non-fatal.
- `references/quality-tier-encoder-ladder.md` — Ultra/Balanced/Compatibility bpp+preset ladder; camera-active Compatibility caps capture 1600×1000 @24fps; one-way OOP-muxer fallback to in-process.
- `references/display-notch-resolution.md` — notch recorded only for full-display captures; area captures rebase fractions ONLY when fully contained with top edge at 0.
- `references/system-audio-epoch-anchor.md` — intermittent sources (WASAPI loopback) anchor at PipelineEpoch so a late first sound can't trim other tracks' heads.
- `references/instant-recording-health-classification.md` — disk-evidence health ladder init+segments=Healthy / init-only=Degraded / none=Damaged; Drop always finalizes via Stop, never cancels.
- `references/aspect-aware-clamp-size.md` — four aspect branches (16:9-ish, 9:16-ish, ultrawide, ultratall) with even-dimension post-rounding; ratio fidelity over budget.
- `references/recording-spool-liveness-contract.md` — IndexedDB spool with updatedAt heartbeat (15s) + 3-min idle window so recovery sweeps never delete live sessions; single-writer queue latch-on-error.
- `references/multipart-uncertain-completion.md` — complete-call retry where post-transient definitive rejection = MultipartCompletionUncertainError; every control-plane call timed.
- `references/streaming-part-upload-economics.md` — 5MiB parts, 3 slots, 128MiB enqueue-time overflow guard, online-gated exponential backoff, Drive Content-Range dialect.
- `references/displaymedia-retry-ladder.md` — preferred→no-prefs→no-audio attempt ladder; cancellation never retried; limiter destination identity stable for live mic swaps.
- `references/recording-pipeline-selection.md` — Chromium-only streaming preference; hasAudio flips candidate order; codec labels parsed from negotiated mime, never assumed vp9/opus.
- `references/capped-local-backup-strategy.md` — pure reducer backup state machine; overflow clears ALL chunks and latches (MediaRecorder chunks are only head-playable).

## Capsule map
- **StudioRecordingActorFsm** — `studio-recording-actor-fsm`: take-state actor FSM keeping segment indices and cursor ids continuous through pause/resume cycles.
- **RequiredVsOptionalTrackFailure** — `required-vs-optional-track-failure`: exactly-once failure ledger keyed (track, stage); optional-track death degrades, display death completes-as-error.
- **CrossTrackStartTimeSnapping** — `cross-track-start-time-snapping`: derived one-audio-frame threshold snapping with fixed reference precedence.
- **VfrMediaSpanDuration** — `vfr-media-span-duration`: persisted display duration = last−first muxed timestamp + 1/fps, two-step fallback.
- **FragmentManifestRecoveryLadder** — `fragment-manifest-recovery-ladder`: three-tier fragment admission with torn-write size gate.
- **TmpRescueAndRespawnGroups** — `tmp-rescue-and-respawn-groups`: tail-complete promotion, corrupt markers, isolated respawn-group remux.
- **RecoveryStartTimeFallback** — `recovery-start-time-fallback`: `.or(display)` start-time inheritance preserving editor offsets.
- **DisplaySyncSpanInvariant** — `display-sync-span-invariant`: asymmetric short/long container-duration cross-check at both finalize sites.
- **AtomicManifestWrites** — `atomic-manifest-writes`: durable JSON write ordering + InProgress beacon lifecycle.
- **QualityTierEncoderLadder** — `quality-tier-encoder-ladder`: quality tiers → bpp/preset/caps with conditional camera-active degradation.
- **DisplayNotchResolution** — `display-notch-resolution`: containment-gated notch rebasing into frame fractions.
- **SystemAudioEpochAnchor** — `system-audio-epoch-anchor`: anchor policy matched to source delivery semantics.
- **InstantRecordingHealthClassification** — `instant-recording-health-classification`: evidence-based health grading + finalize-on-Drop.
- **AspectAwareClampSize** — `aspect-aware-clamp-size`: four-branch resolution clamp with evenness enforcement.
- **RecordingSpoolLivenessContract** — `recording-spool-liveness-contract`: heartbeat/idle-window liveness protecting cross-tab crash backups.
- **MultipartUncertainCompletion** — `multipart-uncertain-completion`: completion ambiguity as first-class error state.
- **StreamingPartUploadEconomics** — `streaming-part-upload-economics`: buffered part assembly under memory/backpressure limits.
- **DisplaymediaRetryLadder** — `displaymedia-retry-ladder`: preference-degradation ladder + stable-output audio mixer.
- **RecordingPipelineSelection** — `recording-pipeline-selection`: capability-driven pipeline + derived codec metadata.
- **CappedLocalBackupStrategy** — `capped-local-backup-strategy`: all-or-nothing capped backup reducer.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
cap (AGPL-3.0; MIT exception covers only cap-camera*/scap-* crates, neither mined — patterns only, never verbatim), `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory project `ext-cap` (52,211 nodes / 214,241 edges @ HEAD 0ce9e675, indexed 2026-08-23T23:33Z; parse_partial ×45 = wgsl shaders, SQL migrations, CSS — no mined seam affected; pnpm-lock + vendor excluded by design). Pass 1 mined crates/recording (14,668 LOC src whole-file) + packages/recorder-core (2,434 LOC whole-file incl. tests).

## Full view (memory graph)
Revalidate `ext-cap` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: FSM transition rules, failure ledgers, snap/clamp/duration math, liveness windows, retry-and-uncertainty ladders, atomic write recipes. Adapt platform plumbing: kameo actors, ffmpeg muxers, IDB stores, XHR uploads. Omit product behavior: Cap's sharing/upload SaaS routes, Tauri/desktop shell wiring, macOS AVFoundation session internals, and any AGPL source verbatim copying (license boundary — borrow WHY, never files).
