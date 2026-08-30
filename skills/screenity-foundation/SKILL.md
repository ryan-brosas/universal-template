---
name: screenity-foundation
description: Use when porting Chrome-extension recording machinery from screenity — WebCodecs fast-recorder capability gate (probe ladder, sticky device-disable TTL, transient classification), MediaRecorder fallback swap, start-gate stream-readiness races, background alarm watchdogs (first-chunk evidence ladder, stall recovery), output-blob validation taxonomy, the MV3 message-router response contract, and the CloudRecorder upload-telemetry/session-recovery kernel (BG-forward survival relay, serialized event ring store, fan-in hub, typed request allowlist, send degradation ladder, dual status machines, post-crash journal sweep and download-then-clear rescue).
disable-model-invocation: true
---

# screenity: recording-lifecycle foundation

## Use this for
Use when porting or debugging browser-extension media-recording kernels: choosing between
WebCodecs and MediaRecorder at runtime, surviving hardware/driver codec failures without
permanently downgrading users, watchdog ladders that must discriminate "capture died" from
"encoder stalled" from "tab throttled", validating recorded blobs before handing them to an
editor, and cross-context (tab ⇄ service worker) messaging contracts. Source code is ground
truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/fast-recorder-gate-decision.md` — who wins: user setting vs sticky disable vs probe.
- `references/fast-recorder-sticky-disable-ttl.md` — self-healing device-disable lifecycle.
- `references/fast-recorder-probe-cache-single-flight.md` — TTL cache + coalesced probing.
- `references/encoder-roundtrip-support-ladder.md` — config ladder + real encode round-trip.
- `references/fast-recorder-output-validation-taxonomy.md` — hardFail vs informational verdicts.
- `references/webcodecs-in-session-fallback-swap.md` — silent engine swap mid-recording.
- `references/first-chunk-watchdog-evidence-ladder.md` — rearm ladder over recorder snapshots.
- `references/recorder-start-gate-timeout-race.md` — deferred start that re-checks at the timeout tick.
- `references/telemetry-bg-forward-survival.md` — tab→BG relay so events outlive window.close().
- `references/telemetry-store-write-chain.md` — BG ring store: chained RMW, never-throw, mirror key.
- `references/upload-telemetry-fan-in-hub.md` — the one emit point: id ladders, store-always/network-selective.
- `references/telemetry-request-allowlist-fold.md` — typed allowlist, pre-mediaId diag admission, errMsg fold.
- `references/telemetry-network-send-ladder.md` — token ladder, beacon-first unload sends, 404/405/413 kill switch.
- `references/session-status-two-machine-split.md` — uploader-resume set vs session-recovery set.
- `references/stale-journal-post-crash-sweep.md` — destroy resume identity before a fresh session.
- `references/crash-recovery-download-then-clear.md` — backend-aware rescue: download → delayed revoke → clear.

## Capsule map
- **Gate decision** — `fast-recorder-gate-decision`: explicit-off beats sticky-disable beats
  probe-ok; unset user setting stays `null` so the disable path remains reachable.
- **Sticky disable TTL** — `fast-recorder-sticky-disable-ttl`: lazy 14-day expiry on read;
  detailed late reports clear coarse earlier disables in the same attempt.
- **Probe cache** — `fast-recorder-probe-cache-single-flight`: success persists 7 days keyed by
  UA+gate version; failures live 60s in memory only; `_probeInFlight` coalesces; real failure
  invalidates the cached pass.
- **Encoder ladder** — `encoder-roundtrip-support-ladder`: isConfigSupported × size × codec ×
  hw × knob-omission ladder, then 4 synthetic frames through a real encoder under a 1500ms cap;
  error retries once, zero-output never does; 7-day clean-probe trust overrides transient-only misses.
- **Output validation** — `fast-recorder-output-validation-taxonomy`: mediabunny demux under
  timeout; hardFail = no-blob/unexpected-mime/no-video-track; rebuild-timeout is inconclusive,
  never a defect verdict.
- **Fallback swap** — `webcodecs-in-session-fallback-swap`: once-per-session swap to
  MediaRecorder when track is live and zero chunks landed; abort the OPFS writer before re-entry.
- **Watchdog** — `first-chunk-watchdog-evidence-ladder`: bounded snapshot, five rearm reasons,
  muted-track starvation is not a defect, live+unmuted+no-chunk is.
- **Start gate** — `recorder-start-gate-timeout-race`: four-way request dedup; the timeout
  handler re-checks readiness first so a just-arrived stream is a race win, not an error.
- **BG-forward survival** — `telemetry-bg-forward-survival`: telemetry writes relay to the
  service worker because window.close() races tab-side storage IPC; flush = allSettled under
  a 1500ms cap so a wedged BG can't block close.
- **Store write chain** — `telemetry-store-write-chain`: promise-chained read-modify-write
  over a slice(-300) ring; never throws (returns false + loud warn); mirrors newest event.
- **Fan-in hub** — `upload-telemetry-fan-in-hub`: one emit point (26 callers) stamps id
  fallback ladders, caller payload spreads LAST, store-always, network-sent except progress.
- **Request allowlist** — `telemetry-request-allowlist-fold`: typed allowlist drops unknown
  root keys; DIAG_EVENT_TYPES admit pre-mediaId diagnostics; errMsg||message||error fold.
- **Send ladder** — `telemetry-network-send-ladder`: token ref→storage→API; beacon-first for
  unload events; 404/405/413 permanently disables network sends.
- **Status machines** — `session-status-two-machine-split`: RESUMABLE_UPLOADER_STATUSES gates
  resume() (+failure-counter reset); RECOVERABLE_SESSION_STATUSES ∧ durable chunks gates crash
  recovery — never cross the tiers.
- **Journal sweep** — `stale-journal-post-crash-sweep`: journals + lookup keys + video-map +
  sceneId reset in one sweep; telemetry fires BEFORE deletion.
- **Crash rescue** — `crash-recovery-download-then-clear`: reopen stores by previous session's
  backend; download → delayed (2000ms) objectURL revoke → clear stores → drop OPFS session dir.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question.
Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
screenity (GPL-3.0), `master@e10e375fafa1680de99ca6db36536dd4a1f4f7d4` (tag v4.6.6); Codebase
Memory project `screenity` (FULL, ready, 12,370 nodes / 21,413 edges, generation
2026-08-25T20:03:54Z, head==base zero drift; re-pinned unchanged at pass 2). Pass 1 mined the
recording-lifecycle kernel (8 capsules); pass 2 mined the CloudRecorder upload-telemetry +
session-recovery kernel (+8 capsules). Coverage caveats at pin: 62 parse-partial files
(cosmetic SCSS + isolated JSX lines, none cited by either pass); `package.json` declares
`test:unit` (`node --test tests/unit/*.test.mjs`) and Playwright e2e, but `tests/` ships ZERO
tracked files at this pin — both runners are dangling references, so all Probe fields are
deterministic byte-exact anchors plus live graph retrieves, not executed suites.

## Full view (memory graph)
Revalidate `screenity` before porting: run `index_status`, `check_index_coverage`,
`search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit,
mode, node/edge counts, freshness, and any coverage caveats; source decides shipped claims.
Hotspot map for orientation: `ContentState.setContentState` fan-in 140 and mediapipe wasm
bundle symbols are graph noise, not seams; two real kernels are (a) Background alarms →
`src/media/fastRecorderGate.ts` → Recorder.jsx callbacks → CloudRecorder telemetry, and
(b) `src/pages/CloudRecorder/CloudRecorder.jsx` emitUploadTelemetry fan-in (26 callers) →
BG `cloud-telemetry-event` handler → serializedTelemetryStore write chain, plus the
session-status machines gating resume/recovery around clearStaleUploadJournals.

## Boundaries
Adopt the decision/watchdog/validation contracts (they are host-agnostic state machines).
Adapt every `chrome.*` storage/alarm/tabs surface and React component wiring to your host.
Omit Screenity's product surfaces (editor sandbox, cloud upload endpoints, i18n copy) unless
your port shares those products.
