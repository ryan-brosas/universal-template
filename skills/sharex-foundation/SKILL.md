---
name: sharex-foundation
description: Use when porting ShareX's desktop job kernel — per-task STA worker threads with UI-context event marshaling, bounded upload admission control, state-dependent stop/cancel ladders, retry ladders, after-upload pipelines, and uploader factory/config gates. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.
---

# ShareX: Task lifecycle kernel foundation

## Use this for
Use when porting screenshot/job-queue runtimes, desktop task managers with progress UI, or any capture→process→upload pipeline that needs bounded concurrency, cancellable worker threads with marshaled completion events, and post-upload action chains. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/task-admission-concurrency-gate.md` — how to bound concurrent uploads without a semaphore while re-pumping on every completion.
- `references/worker-task-state-machine-stop-ladder.md` — what Stop() must do in each task state and how terminal status is decided.
- `references/sta-threadworker-context-marshaling.md` — dedicated STA thread per job with SynchronizationContext-posted events.
- `references/thread-dowork-finally-cleanup-contract.md` — cleanup that must survive stop/failure (KeepImage latch, clipboard rollback, deferred delete).
- `references/upload-retry-ladder.md` — fail-retry loop with inter-attempt sleep and stop gating.
- `references/after-upload-job-pipeline.md` — ordered URL post-processing chain gated on IsURLExpected.
- `references/uploader-factory-config-gate.md` — destination resolution: filter override → CheckConfig → CreateUploader, errors as results not exceptions.
- `references/recent-task-bounded-queue.md` — lock-guarded bounded recent-items queue with settings persistence.

### Entry/dispatch plane (pass 2)
- `references/executejob-safe-settings-dispatch.md` — one-time GetSafeTaskSettings normalization before the HotkeyType switch; filePath-vs-picker duality.
- `references/cli-command-dispatch-chain.md` — ordered consume-or-fall-through CLI checker chain; named-workflow settings resolved once; bad args consumed with log.
- `references/clipboard-content-type-ladder.md` — Image→Text→FileDropList priority ladder; ExternalException user-consented recursive retry.
- `references/processtextupload-url-triage.md` — valid-URL three-way flag gate (download/shorten/share) with early returns; folder-index special case.
- `references/runimagetask-deferred-start-recursion.md` — interactive pre-upload gates via skip-flag recursion; single creation closure; dismissal still progresses.
- `references/worker-task-factory-null-contract.md` — factories return null on load failure; TaskManager.Start owns the null guard; History tasks are display-only.
- `references/native-messaging-consume-once.md` — JSON file IPC deleted in finally regardless of parse outcome; per-branch field validation.
- `references/finddatatype-extension-triage.md` — settings-driven extension triage to Image/Text/File at factory time, File as terminal default.

## Capsule map
- **Admission control** — `task-admission-concurrency-gate`: UploadLimit minus working count, clamped, recomputed in every completion's finally.
- **Task FSM / stop** — `worker-task-state-machine-stop-ladder`: InQueue→Preparing→Working→Stopping→{Stopped|Failed|Completed}; Stop is per-state.
- **Thread + marshaling** — `sta-threadworker-context-marshaling`: one STA background thread per task; every On* event posted to the captured SynchronizationContext.
- **Cleanup contract** — `thread-dowork-finally-cleanup-contract`: finally-block owns KeepImage latch, early-copy clipboard rollback, DeleteFile job.
- **Retry** — `upload-retry-ladder`: MaxUploadFailRetry attempts, 1s sleep, stop-requested breaks the loop.
- **Post-upload chain** — `after-upload-job-pipeline`: regex replace → ForceHTTPS → shorten (auto-length) → share → clipboard → open → QR.
- **Uploader resolution** — `uploader-factory-config-gate`: invalid config yields an error UploadResult, never a throw.
- **Recent items** — `recent-task-bounded-queue`: clamp 1..100, dequeue-while-full under lock, persistence side effect outside the lock.
- **Workflow dispatch** — `executejob-safe-settings-dispatch`: sanitize once at switch entry; every branch receives safe copies.
- **CLI entry** — `cli-command-dispatch-chain`: five-checker verb chain, shared up-front workflow settings, URL-vs-file bare-arg triage.
- **Clipboard entry** — `clipboard-content-type-ladder`: fixed content priority + transient-lock retry dialog.
- **Text triage** — `processtextupload-url-triage`: precedence flags pick exactly one action for URL-shaped text.
- **Deferred image start** — `runimagetask-deferred-start-recursion`: menu/window gates recurse forward with skip flags.
- **Factory boundary** — `worker-task-factory-null-contract`: null-on-load-failure absorbed at Start(); status-tested display-only History membership.
- **Extension IPC** — `native-messaging-consume-once`: request file destroyed in finally; decode→download→file-upload degradation rungs.
- **Type stamping** — `finddatatype-extension-triage`: extension-only classification frozen at factory time.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
ShareX (GPL-3.0), `develop@db2bba61232b957f3dfb6a69719d8cfbc7a80c2f`; Codebase Memory project `sharex` (FULL, 35,540 nodes / 96,845 edges @ gen 2026-08-25T20:07:59Z; skipped=0; parse_partial ×6 uncited). Pass 1: worker kernel below `TaskManager.Start` (8 capsules). Pass 2: entry/dispatch plane above it — ExecuteJob, CLI, clipboard/drag-drop/text triage, task factories, extension IPC (8 capsules). No upstream test project exists at this pin — capsules pin behavior via byte-exact source probes instead of test runners.

## Full view (memory graph)
Revalidate `sharex` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: admission arithmetic, per-state stop ladder, context-marshaled events, finally-block cleanup ordering, error-as-result uploader gates. Adapt threading primitives (SynchronizationContext/STA are WinForms-era idioms — port to your runtime's marshaler) and UI surfaces (tray/taskbar progress). Omit product behavior: concrete uploader services, toast/notification windows, OCR/print/QR integrations, and Avalonia presentation code.
