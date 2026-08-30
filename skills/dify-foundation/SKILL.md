---
name: dify-foundation
description: "Use when porting Dify's workflow app-execution spine — long-running LLM workflow execution with cancellation, pause/resume, event streaming to clients, or engine-layer persistence hooks. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
disable-model-invocation: true
---
# Dify: Workflow app-execution spine foundations

## Use this for
Use when porting long-running LLM workflow execution with cancellation, pause/resume, event streaming to clients, or engine-layer persistence hooks. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/coordinator-fsm-watchdog.md` — one coordinator per attempt owns RUNNING→PAUSED/ABORTING/TERMINAL; watchdog cancel-before-callback.
- `references/stale-cancellation-signal-reset.md` — resumed attempts must drain stop flag + queued abort commands or they self-abort.
- `references/stop-aware-ready-queue-enqueue-gate.md` — stopped runs reject successor enqueues silently; queue reads delegate unchanged (#41090).
- `references/listen-loop-ping-latch.md` — 1s-timeout queue poll drives ping cadence, stop detection (TTL-cached), and terminal latch.
- `references/task-belong-ownership-gate.md` — Redis ownership key gates who may arm a task's stop flag.
- `references/sqlalchemy-model-publish-guard.md` — recursive publish guard refuses ORM instances inside queue events.
- `references/publish-side-terminal-stop-listen.md` — publishing a terminal event stops the listener from the producer side.
- `references/celery-warm-shutdown-channel.md` — combined command channel fans in fetches, routes sends to primary only.
- `references/stop-flag-command-channel.md` — legacy Redis stop flag becomes exactly one engine AbortCommand per channel instance (#41090).
- `references/active-task-duplicate-registration.md` — process-local RLock set rejects duplicate live task IDs.
- `references/resumption-context-versioned-envelope.md` — discriminated union envelope serializes entity + runtime state + filter state.
- `references/response-stream-filter-instance-identity.md` — pause-state layer must receive the exact filter instance the entry uses.
- `references/timeslice-cfs-pause-layer.md` — class-level APScheduler job pauses workflows at resource limits.
- `references/generate-worker-thread-split.md` — worker thread runs the graph; request thread streams; contexts carried explicitly.
- `references/worker-thread-leak-bound.md` — bounded 300s join keeps leaked workers from occupying execution slots forever.
- `references/resume-graph-restore-committed-value.md` — resume re-reads the persisted run's frozen graph via set_committed_value.
- `references/skip-user-inputs-trigger-key.md` — sentinel args key bypasses input preparation for trigger-driven runs.
- `references/single-node-graph-subsetting.md` — single-step debug runs filter nodes by iteration/loop membership before Graph.init.
- `references/event-handler-dispatch-table.md` — dict lookup first, isinstance fallbacks second, unhandled events silently dropped.
- `references/node-exception-output-preservation.md` — exception events still persist node outputs; failures do not.
- `references/invoke-result-stream-close-on-stop.md` — provider generators are explicitly closed on GenerateTaskStoppedError.
- `references/multimodal-image-message-file-commit.md` — generated images land as MessageFile rows on an independent session, committed before publish.
- `references/trigger-log-status-map-layer.md` — aborted maps to FAILED, not stopped; elapsed accumulates across segments.
- `references/conversation-variable-selector-filter.md` — conversation scope persists only `conversation.*` selectors with ≥2 segments.
- `references/input-validation-type-ladder.md` — per-type validation → null-byte sanitize → file conversion → shape rejection sweep.
- `references/debugger-only-draft-saver.md` — factory returns a real saver for DEBUGGER runs, Noop for everything else.
- `references/llm-max-token-recalc.md` — overflow-only max_tokens clamp with 16-token floor and use_template alias resolution.
- `references/closed-file-stopped-translation.md` — "I/O operation on closed file." ValueError translates to GenerateTaskStoppedError.
- `references/human-input-email-dispatch.md` — HITL pause fans per-form email tasks onto the mail queue, best-effort after enrichment.
- `references/sse-event-stream-grammar.md` — mapping→data frame, string→event frame; ping bypasses JSON; run_id at top level.
- `references/reasoning-chunk-final-signal.md` — empty reasoning drops unless is_final carries the terminator.
- `references/tts-audio-mime-validation-ladder.md` — schema/chunk/magic-byte MIME claims validated with fatal mismatch semantics (#41043).
- `references/tts-tail-blocking-consume-sentinel.md` — publish(None) sentinel + blocking drain replaces wall-clock TTS tail timeout (#41043).
- `references/workflow-app-log-source-map.md` — audit rows only on INITIAL start; debugger/trigger sources excluded by early return.
- `references/file-access-scope-binding.md` — ambient FileAccessScope bound at entry; class-derived identity; nullcontext fallback.
- `references/snippet-start-node-reapply.md` — virtual Start injection re-applied after the worker reloads the workflow from DB.
- `references/system-user-id-source-split.md` — external calls use end-user session id; internal calls use account id; resolved once.

## Capsule map
- **Cancellation & lifecycle** — `coordinator-fsm-watchdog`, `stale-cancellation-signal-reset`, `listen-loop-ping-latch`, `task-belong-ownership-gate`, `stop-aware-ready-queue-enqueue-gate`: one attempt-scoped FSM coordinates user stops, timeouts, pauses, and listener detachment over Redis signals.
- **Queue & event transport** — `sqlalchemy-model-publish-guard`, `publish-side-terminal-stop-listen`, `event-handler-dispatch-table`, `node-exception-output-preservation`, `conversation-variable-selector-filter`: events flow producer→queue→dispatcher→SSE without leaking ORM objects or losing outputs.
- **Command channels & guards** — `celery-warm-shutdown-channel`, `stop-flag-command-channel`, `active-task-duplicate-registration`: multi-source abort commands plus process-local duplicate-run protection.
- **Pause & resume** — `resumption-context-versioned-envelope`, `response-stream-filter-instance-identity`, `resume-graph-restore-committed-value`: versioned serialized envelopes restore exactly what a paused segment lost.
- **Generation orchestration** — `generate-worker-thread-split`, `worker-thread-leak-bound`, `skip-user-inputs-trigger-key`, `single-node-graph-subsetting`, `snippet-start-node-reapply`, `system-user-id-source-split`: thread-split generation with bounded joins, identity resolution, and debug subgraphs.
- **LLM streaming & side effects** — `invoke-result-stream-close-on-stop`, `multimodal-image-message-file-commit`, `llm-max-token-recalc`, `reasoning-chunk-final-signal`, `sse-event-stream-grammar`, `tts-audio-mime-validation-ladder`, `tts-tail-blocking-consume-sentinel`: prompt-stream consumption that honors cancellation and persists artifacts safely, rendered to the SSE wire; TTS audio rides a validated MIME ladder and a sentinel-driven tail drain (#41043).
- **Inputs & access** — `input-validation-type-ladder`, `debugger-only-draft-saver`, `file-access-scope-binding`, `closed-file-stopped-translation`: untrusted inputs become typed safe variables behind scoped authorization.
- **Engine layers & bookkeeping** — `timeslice-cfs-pause-layer`, `trigger-log-status-map-layer`, `human-input-email-dispatch`, `workflow-app-log-source-map`: GraphEngineLayer hooks for resource pausing, trigger logs, notifications, and audit rows.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
dify (Apache-2.0 with additional conditions — multi-tenant branding/restrictions), `main@44aec257bf70de70596961dd11305572760260f6` (pass-1 @ `8bdf702f`, pass-2 drift re-entry ff-pulled +40 upstream commits); Codebase Memory project `ext-dify` (294,626 nodes / 1,000,188 edges at the pass-1 pin, ready, FULL mode; parse_partial ≈200 files = .env/.css/spec fixtures + icon SVGs, none cited).
PASS-2 DRIFT RE-ENTRY (2026-08-24): mined `ab34f9ae` (#41090 stop-between-non-streaming-nodes → stop-aware-ready-queue-enqueue-gate + stop-flag-command-channel) and the `3f7e6cdc` (#41043 TTS audio-MIME rewrite → tts-audio-mime-validation-ladder + tts-tail-blocking-consume-sentinel); repaired spans/counts on 9 drift-touched capsules (coordinator-fsm-watchdog, stale-cancellation-signal-reset, celery-warm-shutdown-channel incl. `_abort_emitted` 4→8, event-handler-dispatch-table, node-exception-output-preservation, reasoning-chunk-final-signal, workflow-app-log-source-map, system-user-id-source-split, closed-file-stopped-translation); real-runner battery via repo venv pytest (`-p no:cacheprovider -o addopts=` to defeat coverage addopts): 35+47 green across new/touched suites.

## Full view (memory graph)
Revalidate `ext-dify` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Note: the workflow GRAPH ENGINE itself lives in the pinned external `graphon==0.7.0` dependency (not in this repo); this foundation covers dify's own app-execution surface around it.

## Boundaries
Adopt pure contracts: coordinator FSM + watchdog discipline, stale-signal reset ladder, listen-loop ping/latch semantics, SQLAlchemy publish guard, dispatch-table ordering, resumption envelope shape, worker-thread join bounds, stop-aware enqueue gating with silent successor drops, exactly-once flag→AbortCommand translation, three-source MIME validation with fatal mismatch semantics. Adapt host-specific integrations: Redis key naming, Celery warm-shutdown wiring, APScheduler deployment, Flask context propagation, Dify model-runtime/plugin plumbing (`graphon` package). Omit product behavior: EasyUI chat/completion pipelines, web console UI (`web/`), plugin marketplace, billing/enterprise gating, rag-pipeline runner variant, agent-skill management subsystem (`services/skill_management_service.py`, #39675 — separate porting question).
