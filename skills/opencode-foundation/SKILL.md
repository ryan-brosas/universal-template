---
name: opencode-foundation
description: "Use when building client/server coding-agent harnesses: shadow-git snapshot undo, deferred-suspension permission models, protocol-first API codegen, and multi-surface clients."
disable-model-invocation: true
---
# OpenCode Foundation

## Use this for
Client/server coding-agent harnesses: shadow-git snapshot undo, a deferred-suspension permission model, protocol-first API codegen, and multi-surface clients. Source and tests are the contract; references resolve to decisive excerpts and flows.

## Load the matching source dump
- `references/snapshot.md` — shadow-git undo: alternates seeding, ignore-drift correction, semaphores, NUL pathspecs.
- `references/permissions.md` — ruleset evaluation, Deferred suspension, rejection-as-feedback, session-scoped approval.
- `references/sessions.md` — event-sourced persistence, fork-as-graph-rewrite, patch semantics, stream guards.
- `references/editing.md` — nine-replacer fuzzy edit chain, collision triad, locked edit transactions, four-pass applier.
- `references/write-tool.md` — permission-gated full-file write, BOM preservation, format re-sync, LSP feedback.
- `references/read-tool.md` — offset/limit paginated reads, `more` flag, directory listing.
- `references/grep-glob-tools.md` — ripgrep-backed content/file search, include filtering.
- `references/apply-patch-tool.md` — parse-verify-apply hunks, zero-hunk failure, trailing-newline guarantee.
- `references/task-tool.md` — subagent delegation, foreground/background modes, non-overlap guidance.
- `references/shell-tool.md` — bounded cross-platform shell, default timeout, safe env expansion.
- `references/truncate-tool.md` — line+byte-bounded output, spill-to-file with outputPath.
- `references/skill-tool.md` — name-based skill loading.
- `references/question-tool.md` — mid-turn user questions.
- `references/tool-schema.md` — Effect Schema → JSON Schema for tool params.
- `references/lsp-tool.md` — LSP diagnostics feedback loop.
- `references/web-tools.md` — webfetch + websearch.
- `references/plugin-loader-pipeline.md` — staged resolve/load pipeline, Bun failed-import permanence, file-plugin retry ladder.
- `references/plugin-entrypoint-resolution.md` — exports→main→index entry ladder with containment jail and npm/file asymmetries.
- `references/config-plugin-origins.md` — provenance-preserving plugin origin merge across config layers; later-wins dedupe.
- `references/plugin-hook-runtime.md` — parallel load / sequential hook registration, per-phase error isolation, dispose finalizers.
- `references/plugin-meta-fingerprint.md` — cross-process plugin-meta store classifying loads first/updated/same via fingerprints.
- `references/plugin-config-patching.md` — lock-per-file JSONC surgical patching with add/replace/noop modes and descending-index deletion.
- `references/session-fork.md` — chronological-prefix fork with old→new ID remapping and fail-closed unknown cutoff.
- `references/session-patch-usage.md` — single patch funnel with tri-state clear semantics + cross-provider usage→cost math.
- `references/prompt-loop-exit-machine.md` — four-clause loop-exit gate; stop-finish with live tool calls keeps running; interrupted orphans never prefill.
- `references/prompt-subtask-dispatch.md` — subtask parts execute as real Task tool calls; error-as-data part states preserve child metadata.
- `references/prompt-structured-output-capture.md` — StructuredOutput tool injection, toolChoice:"required", closure capture, missing-call error.
- `references/prompt-content-filter-surfacing.md` — content-filter finishes become persisted+published message errors while keeping partial output.
- `references/command-template-engine.md` — slash-command $N/$ARGUMENTS/!`cmd`/@file expansion order and last-placeholder-variadic rule.
- `references/prompt-title-guardrails.md` — at-most-once auto-titling: parent/default-title/one-real-message gates + think-strip + 100-char clamp.
- `references/file-part-resolution-ladder.md` — @file/data:/MCP-resource/agent parts fan out to synthetic transcript pieces; failures are narratives, not errors.
- `references/session-run-state-kernel.md` — runner-per-session mutual exclusion, queued callers, latch-gated shells, transitive background-job cancel waves.
- `references/prompt-shell-as-user-message.md` — user-run shell recorded as model-shaped assistant tool call with streamed output metadata + abort narrative.
- `references/plan-mode-reminder-injection.md` — plan/build mode-switch reminders as synthetic last-user parts; legacy vs experimental plan-file regimes.
- `references/instruction-discovery-claims.md` — AGENTS.md/CLAUDE.md first-match ladders, once-per-message claims ledger, history-derived dedup.
- `references/system-prompt-family-selection.md` — pure substring model→base-prompt routing and canonical system block order (env→instructions→mcp→skills).
- `references/prompt-tools-permission-projection.md` — per-prompt tools map REPLACES session permission rules wholesale (not a merge).
- `references/session-model-persistence-ladder.md` — sticky session model via DB row → user-message scan → provider default; diff-gated writes; conditional variant inheritance.
- `references/session-context-budget-ladder.md` — usable-context arithmetic (input-cap vs context−maxOutput, 20k buffer) + recency-first budgeted tail-turn selection with mid-turn split.
- `references/compaction-replay-choreography.md` — compaction as a special assistant turn over the normal processor; prior-summary pair-hiding; overflow replay with media→text substitution and unstable continue marker.
- `references/tool-output-prune-ladder.md` — marking-not-deleting prune of old tool outputs; dual thresholds (40k protect / 20k minimum), protected tools, already-pruned frontier stop.
- `references/provider-error-retry-policy.md` — retryable classification precedence (overflow never retries; 5xx forces retryable; Go-limit upsell actions) + dual-cap backoff honoring retry-after headers.
- `references/llm-runtime-seam.md` — native-vs-AI-SDK runtime selection with logged fallback reason; broken-tool-call case-fix→invalid-sink repair; workflow toolExecutor value-not-throw bridge.
- `references/summary-git-path-unquote.md` — step-start/step-finish snapshot diff pairing; byte-buffer decoding of git quoted/octal paths.
- `references/session-status-ledger.md` — ephemeral per-instance busy/idle map; publish-before-mutate; idle evicts instead of storing.
- `references/session-processor-event-machine.md` — LLM stream events → session parts state machine; pre-stream snapshot capture; compact/stop/continue turn result; ensuring-cleanup.
- `references/doom-loop-guard.md` — 3-repeat trailing-window canonical-JSON detector raises a `doom_loop` permission ASK with always-whitelist, never a hard fail.
- `references/tool-call-cleanup-ladder.md` — abort cleanup: 250ms grace-await on tool Deferreds then force-close as error with `interrupted:true`; runs under ensuring on every exit path.
- `references/network-error-finish-conversion.md` — finish-step `rawFinishReason:"network_error"` fails the event into the retry policy; unknown error bodies fall through as retryable api_error; loop-exit treats finish `"unknown"` as non-terminal.
- `references/ws-session-pool-fallback.md` — per-session WebSocket pool for POST /responses streaming: busy→HTTP, sticky fallback latch, shared 5-failure budget, 1009 instant fallback, age/idle rotation.
- `references/ws-responses-stream-adapter.md` — Responses-over-WebSocket protocol: one response.create frame in, SSE frames out; terminal-frame grammar; completed one-shot latch; idle-timeout watchdog.
- `references/subagent-failure-propagation.md` — Task tool post-await gate: child message-error or last errored tool part fails the parent call with a `task_id` envelope instead of returning partial text.
- `references/cloudflare-gateway-routing.md` — gateway models route by prefix to native passthrough SDKs (Responses/Messages APIs); only Workers AI receives the Cloudflare token upstream; npm override fires before variant computation.
- `references/httpapi-route-assembly.md` — protocol-owned groups + legacy groups composed into one Effect HttpApi tree; middleware placement vs injected service keys; lazy /doc.
- `references/sse-event-stream-contract.md` — eager-subscribe SSE kernel: no lost events during body startup, directory filter, disposed-frame termination, 10s heartbeat, proxy-defeating headers.
- `references/sync-fence-cursor.md` — x-opencode-sync response-header cursor: pre/post event-sequence diff on mutations, strict parse, blocking wait for replica catch-up.
- `references/http-auth-ladder.md` — loopback auth: auth_token query beats Basic header (EventSource), config-absence disables auth, three tiers, why HttpApiSecurity alternatives are avoided.
- `references/workspace-routing-proxy-fence.md` — tagged request plan (Invalid/Missing/Local/Remote), directory ladder, session-precedence, remote proxy with fence-blocked read-your-writes.
- `references/openapi-public-transform-codegen.md` — PublicApi spec transform repairing Effect OpenAPI bugs + freezing legacy SDK shape; hey-api codegen with fail-loud post-patches.
- `references/deferred-disposal-ws-shutdown.md` — WeakMap request-keyed post-response disposal handshake; WS tracker closing latch with per-socket 1s timeout shutdown.
- `references/httpapi-error-body-shaping.md` — defect-only error boundary with err_ refs, 1KB schema-reason cap (DoS/secret-echo guard), dual-shape error bodies by API generation, CORS Vary merge fix.

## Capsule map
- **Shadow-git undo** — `references/snapshot.md`: per-worktree hidden repo, SHARED object DB via alternates, ignore-drift correction.
- **Permission model** — `references/permissions.md`: last-match-wins rulesets, defer-on-ask, Deferred suspension.
- **Sessions & editing** — `references/sessions.md`, `references/editing.md`: event-sourced persistence, fork-as-rewrite, replacer chain, locked edits.
- **The write path (tools)** — `references/write-tool.md`, `read-tool.md`, `apply-patch-tool.md`, `grep-glob-tools.md`: permission-gated write, paginated read, patch apply, ripgrep search.
- **Execution & delegation** — `references/shell-tool.md`, `task-tool.md`, `truncate-tool.md`: bounded shell, subagent delegation, spill-to-file truncation.
- **Model-facing helpers** — `references/skill-tool.md`, `question-tool.md`, `tool-schema.md`, `lsp-tool.md`, `web-tools.md`: skill loading, user questions, schema conversion, LSP feedback, web access.
- **Plugin system** — `references/plugin-loader-pipeline.md`, `plugin-entrypoint-resolution.md`, `config-plugin-origins.md`, `plugin-hook-runtime.md`, `plugin-meta-fingerprint.md`, `plugin-config-patching.md`: staged loading, entry jail, origin provenance, hook isolation, change fingerprinting, config patching.
- **Session lifecycle** — `references/session-fork.md`, `session-patch-usage.md`: fork-as-ID-rewrite over the chronological prefix; patch funnel + usage/cost accounting.
- **Prompt turn engine** — `references/prompt-loop-exit-machine.md`, `prompt-subtask-dispatch.md`, `prompt-structured-output-capture.md`, `prompt-content-filter-surfacing.md`, `command-template-engine.md`, `prompt-title-guardrails.md`: loop-exit predicate with orphan carve-outs, subtask-as-Task-call dispatch, forced structured capture, finish-as-error surfacing, command template grammar, one-shot titling.
- **Prompt input plane** — `references/file-part-resolution-ladder.md`, `plan-mode-reminder-injection.md`, `instruction-discovery-claims.md`, `system-prompt-family-selection.md`, `prompt-tools-permission-projection.md`, `session-model-persistence-ladder.md`: fail-open file fan-out, synthetic mode reminders, claims-ledger instruction dedup, substring prompt routing, replace-semantics permission projection, sticky model ladder.
- **Run-state & shell** — `references/session-run-state-kernel.md`, `prompt-shell-as-user-message.md`: runner-per-session exclusion + queued callers; user-shell as model-shaped transcript records.
- **Turn processor (pass 5)** — `references/session-processor-event-machine.md`, `doom-loop-guard.md`, `tool-call-cleanup-ladder.md`: LLMEvent→part state machine with compact/stop/continue result; trailing-window repeat-call permission ask; settle-then-force-close abort ladder.
- **Network-error conversion (pass 5)** — `references/network-error-finish-conversion.md`: untrustworthy finish reasons become retryable failures before persistence; unknown error bodies fall through as retryable api_error.
- **Responses-over-WebSocket plane (pass 5)** — `references/ws-session-pool-fallback.md`, `ws-responses-stream-adapter.md`: per-conversation socket pool with sticky HTTP fallback + shared retry budget; WS JSON→SSE bridge with single-terminal grammar.
- **Subagent & gateway planes (pass 5)** — `references/subagent-failure-propagation.md`, `cloudflare-gateway-routing.md`: post-await child-failure gate with task_id envelopes; prefix-routed passthrough SDKs and the Workers-AI-only upstream-key rule.

- **Session context & compaction (pass 4)** — `references/session-context-budget-ladder.md`, `references/compaction-replay-choreography.md`, `references/tool-output-prune-ladder.md`: usable-context arithmetic + budgeted tail selection; summary-pair hiding + overflow replay; marking prune with dual thresholds.
- **Provider failure & runtime planes (pass 4)** — `references/provider-error-retry-policy.md`, `references/llm-runtime-seam.md`: retryable ladder + header-aware backoff; dual-runtime stream seam + tool-call repair + workflow bridge.
- **Turn bookkeeping (pass 4)** — `references/summary-git-path-unquote.md`, `references/session-status-ledger.md`: snapshot-pair diffs + git path unquoting; ephemeral status ledger.
- **HTTP API server plane (pass 6)** — `references/httpapi-route-assembly.md`, `sse-event-stream-contract.md`, `sync-fence-cursor.md`, `http-auth-ladder.md`, `workspace-routing-proxy-fence.md`, `openapi-public-transform-codegen.md`, `deferred-disposal-ws-shutdown.md`, `httpapi-error-body-shaping.md`: typed route composition (protocol-owned groups, per-tier middleware), SSE wire contract with eager subscription + disposed termination, mutation cursor fences over x-opencode-sync, query-first loopback auth ladder, workspace request-plan routing with fence-blocked remote proxying, legacy-freezing OpenAPI transform + fail-loud SDK codegen patches, post-response disposal handshake + WS shutdown registry, bounded dual-shape error bodies.

## Extending the foundation
Add one references-fileshaped capsule per portable seam: one loader line, one grouped map entry, decisive source with an invariant, direct-test probe, and `search_graph` retrieval.

## Provenance
Indexed in Codebase Memory as `opencode` (`/mnt/hdd/utopia/inspo/opencode`, live symlink into `coding-agents/opencode`); 64,966 nodes / 235,651 edges @ `dev@0352100`. Pass 2 re-entry @ `dev@4643e65a`. Pass 3 (deep lane) mined the session prompt plane whole-file at the same pin: 14 new capsule-v2 across prompt.ts (1,631L), run-state.ts, reminders.ts, instruction.ts, system.ts — probes pinned to prompt.test.ts (30+ `it.instance` cases), instruction.test.ts, structured-output.test.ts; check_index_coverage no_recorded_issue on all six cited paths. Pass 4 (deep-rover re-entry, same pin, zero drift): executed pass-3's queued session-context conditionals — compaction.ts (608L whole), overflow.ts, retry.ts (208L), llm.ts (404L), status.ts, summary.ts, message-error.ts read top-to-bottom → 7 capsule-v2 above; probes pinned to compaction.test.ts (:384/:408/:420/:626/:814), retry.test.ts (:260/:269/:282/:294 + delay matrix :35-150), llm.test.ts (:1347/:1514). Pass 5 (drift re-entry @ `dev@0352100`, +116 upstream commits from 4643e65, re-indexed IN PLACE via live-symlink root — no twin): executed queued target #1 (session/processor.ts ALL 718L whole-file) + diff-first triage of the wave → 8 new capsule-v2 (processor machine ×3, network-error conversion trio, WS pool+adapter pair) + drift notes on provider-error-retry-policy / prompt-loop-exit-machine / session-patch-usage; probes pinned to openai-ws.test.ts (32 tests) and test/provider/error.test.ts; graph refreshed 64,850n→64,966n head==base==0352100. Pass 6 (dedicated lane miner-opencode, SAME pin 03521003fafd re-verified live head==base; first pass with a durable work record at inspo/opencode-work/, stale ledger row reconciled): mined the previously-uncited HTTP API server plane — server/routes/instance/httpapi/{api,server,public,lifecycle,websocket-tracker}.ts + middleware/{fence,authorization,workspace-routing,instance-context,error,schema-error,cors-vary}.ts + handlers/groups/event.ts + shared/fence.ts + bus/global.ts + protocol/src/api.ts + protocol/src/groups/event.ts + sdk/js/script/build.ts read whole → 8 new capsule-v2 above; direct tests read whole: httpapi-{event,public-openapi,authorization,workspace-routing,cors-vary,schema-error-body}.test.ts; check_index_coverage no_recorded_issue on all 15 cited source/test paths; 15 byte-exact grep probes GREEN pre-write; bun test runner BLOCKED (zero node_modules in inspo checkout; install outside lane file boundary) → deterministic evidence per Gate-5 fallback; license corrected to MIT at this pin (pass-5 ws-pool capsule's "Slate-licensed" note is stale). Confirm every claim against source — the graph is an index, not truth.

## Boundaries
Adopt shadow-git undo, deferred-suspension permissions, event-sourced sessions, the tool write-path, and the plugin pipeline (staged loader + origin provenance + fingerprinted meta); adopt the prompt turn engine + input plane + run-state kernel contracts from pass 3; adopt the session context/compaction/retry/runtime-seam contracts from pass 4; adopt the turn-processor state machine, doom-loop ask-don't-fail guard, cleanup ladder, and network-error conversion contracts from pass 5; adopt the HTTP API server-plane contracts from pass 6 (typed route assembly, eager-subscribe SSE, sync-cursor fences, query-first auth, workspace request-plan routing with fence-blocked proxying, spec-transform codegen, deferred disposal/WS shutdown, bounded error bodies); adapt the client surfaces, Effect/Layer wiring, and transport; omit site-specific TUI, cli/cmd/run product surfaces, built-in auth plugins, per-cli behavior, OpenAI-specific WS protocol constants, gateway billing sentinel details, and the v2-protocol handler bodies not yet cited unless a target requires them.
