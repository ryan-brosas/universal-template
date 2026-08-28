---
name: cline-foundation
description: "Use when porting Cline's agentic-runtime core — context compaction (trigger budget, overflow-recovery ladder, safe cuts, no-LLM fold), compaction state projection with prefix hashes, runtime safety (loop detection, mistake tracker), pending-prompt steer/queue gate, local hub-daemon transport plane (discovery record, mkdir-lock mutex, ensure/retire ladders, WS envelope, subscription refcounts), claim-once env sentinels with supervised-child restart/adoption, hub command router (authority/drain gates, degraded replies), monotonic shutdown coordination, disk-truth cron reconciliation, agenda task persistence kernel (run-admission gates, exactly-once terminals, crash triage, revision+content-hash CAS), strict/tolerant Markdown intent grammars, location containment, todo-tool scope gate, workspace file-index TTL worker, @mention budget matching, ACP stdio bridge (stdio hygiene, fail-closed permissions, streaming/replay, session lifecycle, config options). Source code and direct tests are ground truth."
---

# Cline: agentic coding-agent runtime core

## Use this for
Use when porting context-window management for LLM agents (compaction triggers from token estimates, summarizer input/output budgeting, deterministic transcript folds, tool-pair-safe cuts), compacted-session persistence and re-projection across restarts, run-safety guards (repeated-tool-call loop verdicts, consecutive-mistake budgets with overridable stop decisions), or typed-ahead prompt queuing with steer semantics. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/compaction-trigger-budget.md` — when a request actually crosses the window: three-rung limit ladder + request-level 90% trigger.
- `references/overflow-recovery-ladder.md` — recovery after provider rejection must never need another successful LLM call.
- `references/safe-cut-boundary.md` — why assistant messages are safe summary cuts and tool-result-only user messages never are.
- `references/agentic-summarizer-budget.md` — estimate → project → serialize ordering against the SUMMARIZER's own window.
- `references/basic-compaction-fold.md` — the deterministic no-LLM funnel with frozen survivors and accumulating stats.
- `references/budget-projection-kernel.md` — reusable shrink-any-transcript algorithm with protections + full action ledger.
- `references/compaction-state-projection.md` — persisted prefix-hash sidecars re-projected onto growing transcripts (the id/ts hashing trap).
- `references/compaction-state-wrapper.md` — projection-first prepareTurn composition keeping auto turns bounded.
- `references/dropped-work-summaries.md` — re-surfacing deleted tool work as SYSTEM_NOTICE blocks with diff-derived edit ranges.
- `references/token-estimator-cache.md` — WeakMap-memoized char-based estimation shared by every comparison.
- `references/summarizer-output-budget.md` — cap-only-lowers output budget; why thinking models return empty summaries.
- `references/compaction-status-notices.md` — started/completed/skipped event contract + documented telemetry gap.
- `references/loop-detection-tracker.md` — canonical-signature consecutive-call detector, soft-once/hard-stop verdicts.
- `references/mistake-tracker.md` — failure counter with forceAtLimit jump, throw-becomes-stop decision resolution.
- `references/pending-prompt-queue.md` — steer-vs-queue delivery, exact-text dedupe, abort-window durability.
- `references/hub-discovery-record.md` — schema-gated reads, atomic temp+rename publication, ownership-scoped clears.
- `references/mkdir-lock-mutex.md` — cross-process mutex from mkdir EEXIST; evidence-gated lock theft; init-window rule.
- `references/detached-hub-ensure-ladder.md` — attach → defer-busy → repair-discovery → spawn+poll state machine.
- `references/hub-build-ordering.md` — tiered build compare whose antisymmetry prevents mutual-retire loops.
- `references/retire-escalation-ladder.md` — drain → shutdown → SIGTERM-at-verified-PID; clear discovery only on confirmed death.
- `references/ws-command-envelope.md` — requestId correlation, delete-before-reject timeouts, never-throw server routers.
- `references/subscription-refcount-reconnect.md` — level-triggered counts / edge-triggered frames, jittered backoff, re-registration.
- `references/env-sentinel-claim.md` — claim-once role markers that cannot leak to spawned grandchildren; propagation-only starting-instance marker.
- `references/connector-supervisor-restart.md` — detached-child supervisor: per-instance lock tails, exponential give-up ladder, mark-before-signal stops, adoption by pid.
- `references/dispatch-command-router.md` — authority-before-dispatch, drain-refusal set, degraded-capability reply duality on one envelope router.
- `references/shutdown-coordinator-monotonic.md` — shared-cleanup-promise shutdown, max() exit escalation, referenced watchdog, deadline-below-retire ordering.
- `references/cron-reconciler-loop.md` — filesystem-as-startup-truth spec reconciliation: scan→upsert→tombstone→refresh, single overdue catch-up.
- `references/team-run-wait-ladder.md` — parked-resolver wait ladder for async teammate runs with finishReason-gated auto-continue.
- `references/agenda-run-admission-gates.md` — ordered fail-closed gate ladder before any session starts; expire-at-admission; claim-before-side-effect.
- `references/agenda-run-completion-races.md` — closed terminal set + re-read-after-await + loser-becomes-observer + guaranteed session abort.
- `references/agenda-crash-recovery-triage.md` — restart triage of interrupted runs; which approvals survive; recovery before reconciliation.
- `references/agenda-store-revision-cas.md` — edit verb (CAS+revision bump+approval revocation) vs lifecycle verb (guarded patch); DDL-carried single-active-run.
- `references/agenda-spec-contenthash-cas.md` — validate-before-write temp+rename publication with expected-content-hash CAS and symlink/containment refusal.
- `references/agenda-file-db-write-ordering.md` — create is DB-first with delete-compensation; update is file-first with restore-compensation.
- `references/agenda-task-command-admission.md` — hub `task.*` commands: identity/scope forced from connection authority after payload spread, existence-hiding scoped lookups.
- `references/agenda-intent-verification.md` — sync reconcile-then-fail-closed ladder binding approval/execution to current Markdown intent via paired field signatures.
- `references/agenda-automation-pump.md` — single-flight microtask pump: measured capacity, provenance vetoes, chain-depth cycle ⇒ ∞, generation-counter mid-pump abort.
- `references/agenda-spec-reconciliation.md` — disk-vs-DB rank table: mint id into file, taskId immutable, defer in_progress, terminal repairs the file, unseen paths archive.
- `references/schedule-command-scope-isolation.md` — top-of-handler registered-workspace scope; existence-hiding schedule lookup; presence-keyed cwd reset via Object.hasOwn.
- `references/schedule-event-mapping.md` — ok-gated reply→event table (five mutating commands) + two-entry internal-outcome filter + awaited/detached trigger twins.
- `references/task-spec-frontmatter-grammar.md` — strict closed-vocabulary task-spec parser: reserved-before-unknown veto, failures-as-data, every failure carries a content hash.
- `references/agenda-task-location-containment.md` — global tasks own no filesystem; workspace paths pass lexical containment THEN realpath walk-up against symlink escapes.
- `references/agenda-spec-serialization-roundtrip.md` — one canonical serializer (fixed field order, presence-keyed spreads) feeding six callers; hash-CAS conditional publishes.
- `references/cron-spec-trigger-grammar.md` — tolerant twin: trigger-kind exclusivity tables instead of vocabularies; stableStringify RAW-body hash; only tools/extensions throw.
- `references/agenda-agent-todo-tool-scope-gate.md` — reduced-verb zod projection over session-derived authority; scope checked on payload AND fetched rows before expected_revision.
- `references/workspace-file-index-ttl-worker.md` — module-level TTL cache whose module IS its worker thread; null-on-timeout same-thread fallback; lone-workspace immortal cache.
- `references/mention-token-extraction-budget.md` — whitespace-anchored @token extraction, linear punctuation trim, prompt-immutability, maxTotalBytes ladder charging the cap constant (maxFiles gate is dead code at pin).
- `references/cron-watcher-debounce-escalate.md` — trailing-edge per-path fs.watch debounce whose filter set mirrors the reconciler walk; deletion escalates to a full reconcile because the single-path handler cannot tombstone.
- `references/event-ingress-suppression-ladder.md` — persist-first replay detection (INSERT OR IGNORE), recursive filter resolution, and the debounce-pushout / dedupe-window / spec-wide-cooldown ladder with a race-guarded UPDATE that falls through to a fresh enqueue.
- `references/acp-stdio-connection-bootstrap.md` — stdout-is-protocol stdio bridge: stderr-only diagnostics, lazy dual import, per-connection agent factory, park on connection.closed, headless-constrained OAuth.
- `references/acp-permission-roundtrip-fail-closed.md` — pending-frame-then-request approval round-trip; cancelled/throw/unknown-option all deny; decision frame always echoed; allow_always is a dead affordance (collapses to allow-once).
- `references/acp-agent-event-streaming-contract.md` — payload-at-start/terminal-at-end streaming: fire-and-forget updates, one-shot text, error-presence tool settlement, end-only media with text degradation.
- `references/acp-session-replay-hygiene.md` — awaited in-order conversation replay: strip user wrappers, replay assistant verbatim, drop synthetic prompts, pending-then-settled historical tool pairing.
- `references/acp-session-manager-lifecycle.md` — lazy idempotent manager persisting the core session under the client-held id; save-before-teardown continuity; one-AbortController cancel; cancelled never surfaces as error.
- `references/acp-config-option-plane.md` — env-pinned provider immutability, teardown-then-re-resolve against the new catalog, single-flight token refresh, rebuild-and-broadcast-all config options.
- `references/connector-thread-binding-kernel.md` — one JSON binding store with control bindings (mutes) in the conversation namespace, skip-on-lookup, DM channel fallback, read-time identity self-heal, delete-don't-tombstone mutes, three-place sessionId scrub.
- `references/connector-thread-turn-queue-key.md` — the queue key mirrors the binding identity (DMs collapse to `dm:{channelId}`); promise-chained Map with catch barrier and identity-checked self-deletion.
- `references/connector-session-reuse-recovery.md` — fail-open on missing hub status, terminal-status rejection, at-most-once stale-mapping retry, expected-id CAS on every mapping clear.
- `references/connector-active-turn-steering.md` — silent steer into the active session (two-rung lookup incl. cross-key); stale steer deletes only the attempted entry and enqueues queue-routed recovery so racers serialize.
- `references/connector-statefile-claim-guard-cas.md` — O_EXCL state-file claim, generation-keyed hard-link guard chain with successor guards, processStartToken pid-reuse defense, content CAS before rm+recreate; poll-ready detached launch with exit-75 and best-effort log tail.
- `references/connector-runtime-event-projection.md` — push/pull bridge converting hub stream events into an async reply iterator: single-slot notify, accumulated-vs-delta rewind keeps text monotonic, failed-latch first-wins, tool status/media/approvals as side channels never entering the text.
- `references/telegram-format-entity-chunking.md` — markdown→entities with NO parse_mode (malformed markdown degrades to raw, not a 400); 4096 chunking with overlap-rebased entity offsets; sent-count-tracked raw fallback resending only the unsent remainder.

## Capsule map
- **Context compaction (`sdk/packages/core/src/extensions/context/`)**
  - `compaction-trigger-budget`: trigger on REQUEST-level estimates at 90% of an effective input limit; window-only models get ×0.9 usable input (81% effective).
  - `overflow-recovery-ladder`: `overflowRecovery` mode bypasses the estimate gate; custom results face non-empty ∧ smaller ∧ ≤target before basic fallback.
  - `safe-cut-boundary`: cut at assistant-or-typed-user boundaries; never orphan a tool_use/tool_result pair; latest typed turn survives verbatim.
  - `agentic-summarizer-budget`: budget messages BEFORE serialization; incremental fold past prior summaries; reasoning-only output ⇒ skip with diagnosis.
  - `basic-compaction-fold`: typed prompts mandatory, attachments only on the latest, kept suffix snaps to an assistant, older finals newest-first, `metadata.compaction:"preserved"` freezes prior output forever.
  - `budget-projection-kernel`: drop-unsafe → truncate-oldest → closure-drop pipeline over a policy matrix with per-action audit trail and explicit `budget_unachievable_with_protections` failure.
  - `dropped-work-summaries`: SYSTEM_NOTICE bridges between merged prompts carry files read (with line ranges)/edited (diff-derived ranges)/commands + up to 3 preserved responses.
  - `token-estimator-cache`: one WeakMap estimator per pipeline; JSON-length ÷ CHARS_PER_TOKEN with prose fallback.
  - `summarizer-output-budget`: 4096 default cap that model metadata can only lower; thinking off; Codex strips maxOutputTokens.
  - `compaction-status-notices`: manual = unprefixed, auto = `auto-`, recovery = `overflow-recovery-`; plus budget-adjusted side channel.
- **Session state (`src/session/models/`)**
  - `compaction-state-projection`: sha256 prefix hash over persisted shape EXCLUDING volatile id/ts; append-only tail projection; legacy boundary rung for v1 sidecars.
  - `compaction-state-wrapper`: re-compaction starts from projection+tail; saveState validated against exactly-hashed sourceMessages.
- **Runtime safety (`src/runtime/safety/`, `src/runtime/turn-queue/`)**
  - `loop-detection-tracker`: sorted-key signatures; soft fires ONCE at exactly 3; hard ≥5 escalates into a forced-limit mistake record.
  - `mistake-tracker`: continue resets to 0; telemetry fires before the decision; callback throws become stop decisions.
  - `pending-prompt-queue`: queue mutates but never drains during abort windows; steer entries unshift and win consume order; error finishes halt draining without requeue.

- **Hub/daemon transport (`src/hub/`: discovery/, daemon/, client/, server/handlers/)**
  - `hub-discovery-record`: defensive schema-gated reads return undefined on malformation; wx-temp + fsync + same-dir rename publication under a `.mutation` mkdir lock; clears are ownership-checked against `hubId` inside the same lock.
  - `mkdir-lock-mutex`: mkdir EEXIST as atomic test-and-set; owner.json {pid, acquiredAt}; steal only on dead PID or expired age; empty-dir initialization window is never stolen before the bounded deadline; fail-fast singleton layer throws typed HubLockHeldError.
  - `detached-hub-ensure-ladder`: discovered+verified ⇒ attach; healthy-but-incompatible ⇒ retire with `deferred_busy` ⇒ attach to busy hubs; reusable hub with missing discovery ⇒ token-candidate loop repairs the record; else spawn detached and poll to a deadline; explicit endpoints skip recoverable-URL memory.
  - `hub-build-ordering`: equal trimmed buildId > finite epochMs > release version > lexicographic id; reuse gate `compareHubBuilds(self, record) <= 0` — older clients attach to newer daemons, newer replace older; corpus test pins antisymmetry (never two mutual retires).
  - `retire-escalation-ladder`: drain (liftable) → authenticated shutdown → SIGTERM only at a positively-alive PID at kill time; discovery cleared ONLY by this function and only after confirmed retirement.
  - `ws-command-envelope`: per-command `hubreq_` requestId in a pendingReplies map; timeout deletes-then-rejects so late replies cannot double-settle; send-failure cleanup; close rejects all pending; server routers convert every throw into okReply/errorReply echoing version+requestId.
  - `subscription-refcount-reconnect`: refcount map per session key; wire frames fire only on 0↔1 edges while OPEN; zero counts stop the reconnect timer; stale closes ignored via socket identity check; backoff = initial·2^attempt capped within jitter band; post-open `client.register` then re-subscribe of every key.
  - `dispatch-command-router`: authority resolved before routing (omitted = trusted in-process, null = remote pre-registration); drain gate refuses only work-admitting commands with retryable `hub_draining`; missing durable queue ⇒ `run_queue_unavailable` error for run.enqueue but OK-empty for run.list.
  - `shutdown-coordinator-monotonic`: all graceful triggers share one cleanup promise; exit code escalates only via max(); 2s watchdog stays referenced and sits BELOW the retire-ladder caller-side wait; forced path exits even when observer hooks throw.

- **Connector supervision (`src/services/connectors/`, `sdk/packages/shared/src/runtime/`)**
  - `env-sentinel-claim`: daemon/supervised markers are claimed once (latch + delete) at entrypoints because every spawned grandchild inherits env — an inherited sentinel made every `cline --help` under a Slack connector die on EADDRINUSE; explicit-env reads bypass the latch; the starting-instance JSON marker propagates instead so the daemon can tell starter from leftover.
  - `connector-supervisor-restart`: NUL-joined instance keys under per-key promise-tail locks; restarts 1s·2^n capped 60s with give-up at 5 consecutive but counter reset after a ≥60s run; stops mark-before-signal then TERM(5s)/KILL(2s); exit continuations re-check entry identity post-await; adopted connectors polled by pid with argv recovered from autostart records; dispose leaves children alive for the next hub.

- **Scheduling & teams (`src/cron/specs/`, `src/session/team/`)**
  - `cron-reconciler-loop`: disk walk (.md, skip reports/) upserts every spec, tombstones unseen DB paths with queued-run cancellation, records invalid parses without aborting; next_run_at resets only on absent/removed/disabled/expr/tz change; catch-up base = max(now, lastRunAt).
  - `cron-spec-trigger-grammar`: kind comes from the PATH (`events/`∧`.event.md` ⇒ event, `*.cron.md` ⇒ schedule, else one_off); cross-kind fields always error via exclusivity tables while unknown extras degrade silently; stableStringify+RAW-body hash twin; tools/extensions are the only throwing vocabularies.
  - `team-run-wait-ladder`: active-run set + pending-update queue + parked resolvers give lossless event-driven waits (abort ⇒ [] immediately); auto-continue needs completed|max_iterations ∧ enableAgentTeams ∧ outstanding work; updates render as mode-formatted system prompts stating remaining-run counts.

- **Agenda task kernel (`src/tasks/`)**
  - `agenda-run-admission-gates`: ordered fail-closed gate ladder (intent → revision CAS → expiry → availability → status → approval-staleness → active-run) before any session; claim (`currentRunId`) written before the side effect.
  - `agenda-run-completion-races`: closed TERMINAL_RUN_STATUSES set + re-read-after-await + loser-becomes-observer; finishRun's finally always clears activeRuns and requeues automation.
  - `agenda-crash-recovery-triage`: restart triage by run status BEFORE reconciliation; a starting run with intact revision+approval restores to approved, everything else degrades to pending_approval/failed.
  - `agenda-store-revision-cas`: edit verb bumps revision+revokes approval under expectedRevision CAS (typed conflict error); lifecycle verb patches status columns under a WHERE-revision guard without bumping; DDL partial unique index enforces one active run per task.
  - `agenda-spec-contenthash-cas`: path+symlink+containment refusal, then serialize→re-parse→validate→temp(0600)→hash-CAS→rename publish; createOnly uses hard-link so target races fail atomically.
  - `agenda-file-db-write-ordering`: create = DB row first then createOnly file write with delete-compensation; update = probe-conflict first, new bytes guarded by old hash, THEN DB bump with restore-compensation.
  - `agenda-task-command-admission`: every task.* command resolves workspace from connection authority or throws; payload spread happens BEFORE forced scope/root/cwd/actor fields, so spoofed identity cannot survive; approve/cancel/run demand positive-integer expectedRevision at the envelope layer.
  - `agenda-intent-verification`: refreshAndVerifyTaskIntent awaits a synchronous scope reconcile (closing the watcher debounce window), then fails closed on archived/missing/unparseable/id-mismatch/signature-mismatch — callers are exactly approveTask/pumpAutomation/runTask.
  - `agenda-automation-pump`: queueMicrotask single-flight pump over queued scopes; capacity = min(concurrency headroom, hourly-start budget); raw file_reconciler intent never self-approves, agent intent gated by applyToAgentCreated, origin-chain cycle ⇒ depth ∞ ⇒ veto; policyGeneration counter aborts an in-flight pump on any policy change.
  - `agenda-spec-reconciliation`: reconcileFileStore ranks — invalid parse logs on; taskId minted into the file once and immutable (edited foreign id rewritten back); in_progress edits defer; completed/cancelled/expired rewrite the FILE to DB truth; unseen paths archive (in_progress cancelled first); fs.watch root needs realpathSync.native because Windows 8.3 short paths abort libuv.
  - `task-spec-frontmatter-grammar`: 14 RESERVED manager keys vetoed BEFORE unknown-field errors over a 16-key ALLOWED vocabulary; hashContent = insertion-order JSON + trimmed body; failures carry `{}`-hashes before YAML parses.
  - `agenda-task-location-containment`: global tasks throw on ANY of workspaceRoot/cwd/resources; resources reject absolute/`..` then pass allowRoot=false containment vs cwd's allowRoot=true; assertNoSymlinkEscape walks up to the nearest existing ancestor and compares realpaths.
  - `agenda-spec-serialization-roundtrip`: fixed-order presence-keyed serializer (lineWidth 0, trimmed body + `\n`) is the SIX-caller funnel (manager createTask/ensureScope/reconcileFileStore/reconcileScope/updateTask + store writeSpec); createInput defaults availableAt to min(now, expiresAt−1).
  - `agenda-agent-todo-tool-scope-gate`: zod admits ONLY create/update/list/get (cancel unrepresentable ⇒ invalid_task_input); session defaults own scope authority; fetched rows scope-checked BEFORE expected_revision demands; telemetry only mutating ops.

- **Hub schedule commands (`src/cron/service/`, `src/hub/server/`)**
  - `schedule-command-scope-isolation`: resolveScope throws before any arm (even list) without clientId+workspaceRoot; requireScopedSchedule hides other workspaces' ids behind "does not exist"; scopedCwd rejects escapes; update cwd is presence-keyed (Object.hasOwn) with explicit null = reset-to-root.
  - `schedule-event-mapping`: schedule commands are the dispatchCommand DEFAULT branch; events publish only when reply.ok AND the five-name mapping hits (create/update|enable|disable/delete/trigger); reads stay silent; internal outcomes filter through a two-entry dot→underscore table; trigger twins differ in await (awaited returns terminal execution, detached returns the enqueued run).

- **Workspace file services (`sdk/packages/core/src/services/workspace/`)**
  - `workspace-file-index-ttl-worker`: 15s TTL hits require fresh ∧ non-empty; pending join single-flights rebuilds behind interim stale entries; eviction only when CACHE.size>1; module doubles as its own unref'd worker with 1s null-on-timeout same-thread fallback; EACCES/EPERM/ENOENT skip-not-fail; fan-in 16 consumers.
  - `mention-token-extraction-budget`: `(^|\s)@token` extraction defeats emails; linear trailing-punct trim regression-pinned vs backtracking; prompt returned unchanged always; maxTotalBytes ladder charges maxFileBytes per admission — the maxFiles gate compares against a never-appended array (dead at pin).

- **Cron watcher & event ingress (`sdk/packages/core/src/cron/specs/cron-watcher.ts`, `sdk/packages/core/src/cron/events/cron-event-ingress.ts`)**
  - `cron-watcher-debounce-escalate`: clear-and-rearm per-path timers (250ms) behind a filter set that mirrors the walk skip set; existsSync=false fires reconcileAll (never reconcileFile, which cannot tombstone); mkdir-before-watch, restartable stop, dispose latch throws.
  - `event-ingress-suppression-ladder`: duplicate eventId short-circuits at the INSERT OR IGNORE before any matching; filters resolve attributes→payload→dot-paths with ANY-of/SOME/recursive-records semantics; debounce UPDATEs a queued run (max push-out, latest triggerEventId) and falls through on race; cooldown is spec-wide regardless of dedupeKey; suppressedCount excludes filter_mismatch.
- **ACP bridge (`apps/cli/src/acp/`)**
  - `acp-stdio-connection-bootstrap`: runAcpMode lazily imports the ACP SDK + AcpAgent, wraps stdin/stdout as an NDJSON stream, writes diagnostics to stderr only (never "error:"-labeled — test-pinned byte-exact), and parks on connection.closed; OAuth runs headless (stderr output, non-blocking browser, reject undefaulted prompts).
  - `acp-permission-roundtrip-fail-closed`: requestAcpToolApproval emits a pending tool_call frame, awaits requestPermission, and maps every outcome through a closed deny-default table; the decision frame is always echoed (in_progress/failed); auto-approve bypasses via a capability closure over the connection; allow_always persists nothing (dead affordance).
  - `acp-agent-event-streaming-contract`: payload-at-start/terminal-at-end streaming; fire-and-forget updates; one-shot text; error-presence tool settlement; media only at end with text degradation.
  - `acp-session-replay-hygiene`: awaited in-order replay; display projection first; user wrappers stripped, assistant verbatim; synthetic prompts dropped; tool_use pending until its tool_result settles.
  - `acp-session-manager-lifecycle`: lazy idempotent manager persisting the core session under the client-held id; save-before-teardown continuity; one-AbortController cancel; empty resume fails closed.
  - `acp-config-option-plane`: env-pinned provider immutability; teardown-then-re-resolve against the new catalog; single-flight token refresh; rebuild-and-broadcast-all options.
- **Connector turn plane (`apps/cli/src/connectors/`)**
  - `connector-thread-binding-kernel`: one JSON binding store; control bindings (mutes) share the conversation namespace and are skipped by every conversation lookup; DM channel fallback; read-time identity self-heal; delete-don't-tombstone mutes; stop scrubs sessionId from root, state, and serializedThread.
  - `connector-thread-turn-queue-key`: the queue key mirrors the binding identity — DMs collapse to `dm:{channelId}` so two messages can never run one session concurrently; promise-chained Map with catch barrier and identity-checked self-deletion.
  - `connector-session-reuse-recovery`: fail-open on missing hub status with send-time session_not_found backstop; terminal-status rejection; at-most-once stale-mapping retry latch; expected-id CAS so an older failure never clears a newer session.
  - `connector-active-turn-steering`: silent steer into the active session via two-rung lookup (exact key, then sessionId+threadId); stale steer deletes only the attempted entry and enqueues recovery through the per-thread queue so racing messages serialize into one replacement session.
  - `connector-statefile-claim-guard-cas`: O_EXCL state-file claim; generation-keyed hard-link guard chain with successor guards (never deleted by contenders); processStartToken pid-reuse defense; content CAS before rm+recreate; poll-ready detached launch, exit-75 already-running, best-effort ANSI-stripped log tail.
  - `connector-runtime-event-projection`: push/pull bridge over a single-slot notify queue; accumulated-vs-delta rewind keeps streamed text monotonic (server shrink ⇒ delta ""); failed-latch makes the first failure win both paths; queued turn is non-error completion; tool status/media/approvals are fire-and-forget side channels; timeoutMs:null.
  - `telegram-format-entity-chunking`: markdown→entities with no parse_mode so malformed markdown degrades to raw instead of a 400; 4096-slice chunking re-bases overlapping entity offsets per chunk; sentPayloadCount-tracked fallback resends only the unsent remainder as raw chunks.


## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Cline (Apache-2.0), `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory project `cline` (FULL mode, refresh 2026-08-25T00:16:42+08:00, 40,351 nodes / 170,446 edges, head==base 4f836ae7, verified against checkout HEAD by git rev-parse during passes 2, 3, 5, and 6; parse_partial limited to tests/proto/CSS/ps1 plus a few core files, none cited unverified — cron-reconciler.ts:60 flagged range read directly; skipped 0). Passes 1–15 capsules were mined under the older `ext-cline` index (40,317 nodes) at the same commit; pass 2 added the 7 hub-transport capsules against the live `cline` index; pass 3 added 6 supervision/routing/shutdown/cron/team capsules at the same pin; pass 5 added the 6 agenda-persistence capsules; pass 6 re-mined the lost pass-4 batch as 6 command/intent-plane capsules and repaired loader/map parity to 40==40==40. Upstream vitest suites exist for every mined plane but were runner-BLOCKED here honestly (clone has no node_modules); gate-5 uses live graph retrieves + fixed-string probe batteries + adversarial wrong-project retrievals. Pass 11 (2026-08-26): the leaf tree was found rolled back to its exact end-of-pass-6 state (40==40; all 22 post-pass-6 reference files absent — fleet-class loss also documented by openhands/dsh-codex/aider/pi-mono lanes); this pass re-executed every evidence chain fresh at the unchanged pin and restored the seven Markdown-intent-grammar capsules (47==47==47); the remaining 15 lost capsules (pass-8 pair, pass-9 ACP set, pass-10 connector set) carry named restoration targets in the work record. Pass 12 restored the pass-8 pair + first two ACP capsules (51==51==51==51); pass 13 (2026-08-26) restored the remaining four ACP capsules (55==55==55==55) with fresh whole-source/test chains — Codebase Memory MCP transport unavailable both passes, direct-read fallback recorded.

## Full view (memory graph)
Revalidate project `cline` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. (Passes 1–15 cite the retired `ext-cline` twin; every capsule since pass 2 cites live project `cline`. Both indexes were pinned to the same checkout commit.)

## Boundaries
Adopt the pure contracts: budget ladders, boundary rules, selection funnels, policy matrices, counters, and queue invariants. Adapt ratio constants, thresholds (3/5, 20k, 4096), tool names, notice copy, and storage locations to host vocabulary. Omit Cline's transport shells (hub server/daemon/websocket around the runtime), VSCode/webview product surfaces, and telemetry vendor plumbing. Team-session coordination is mined (`team-run-wait-ladder`); AgentTeamsRuntime scheduling internals (busy-suppression, retry backoff, mailbox prepend) remain queued as a distinct porting question.
