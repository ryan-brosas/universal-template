---
name: pi-messenger-swarm-foundation
description: "Use when building multi-agent coordination WITHOUT a central database or orchestrator process — durable agent registries with lockless name claiming, append-only event-sourced task queues with claim/dependency/cascade semantics, kafka-like feed messaging that tolerates offline recipients, subagent spawning with concurrency ceilings and crash-reconciled lifecycle tracking, or any port of the pi-messenger-swarm mesh to another agent host. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."

disable-model-invocation: true
---
# pi-messenger-swarm: file-based multi-agent swarm coordination foundation

## Use this for
Use when building multi-agent coordination WITHOUT a central database or orchestrator process — durable agent registries with lockless name claiming, append-only event-sourced task queues with claim/dependency/cascade semantics, kafka-like feed messaging that tolerates offline recipients, subagent spawning with concurrency ceilings and crash-reconciled lifecycle tracking, or any port of the pi-messenger-swarm mesh to another agent host. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/unified-channel-jsonl-store.md` — one JSONL per channel: metadata header on line 1, atomic create-with-first-event, append-only reads.
- `references/session-channel-allocation-ladder.md` — memorable phrase channels restored by sessionId lookup before minting; `-2..-99` suffix ladder.
- `references/registry-write-verify-claim.md` — write-registration → read-back-pid verify as the whole lockless identity story.
- `references/agents-cache-mtime-sync-bridge.md` — mtime-gated self-state sync vs 1s TTL peer cache with per-filter memoization.
- `references/feed-cache-stat-invalidation.md` — 100ms TTL validated by mtime+size pair instead of re-parse.
- `references/task-event-sourcing-replay.md` — nine event types folded deterministically into task state on every read.
- `references/task-claim-guard-ladder.md` — null-returning store gate + handler re-derivation into not_found/already_claimed/already_done/not_ready.
- `references/stale-claim-janitor-throttle.md` — read-triggered 5s-throttled PID-liveness sweep auto-unclaims crashed agents' tasks.
- `references/cascade-reset-dependency-sweep.md` — snapshot done-set BEFORE appending resets; only done dependents reset transitively.
- `references/spawn-concurrency-task-binding-gates.md` — heal-before-count, ready-task nag without `--force`, per-project running limit (default 3).
- `references/spawned-agent-event-lifecycle.md` — partial-merge JSONL spawn log + detached fake-process restore + adopt-don't-duplicate terminal events.
- `references/swarm-protocol-prompt-sandwich.md` — the 10 contract clauses (claim-before-work, evidence-in-record, pull-based feed, exit-on-done) + delegate-don't-claim parent rule.
- `references/harness-identity-resolution-ladder.md` — x-agent-name beats x-caller-pid beats single/most-recent fallback; session mismatch wipes only session channel.
- `references/harness-daemon-lifecycle.md` — lazy start, version-gate restart with spawn preservation, strip PI_MESSENGER_CHANNEL from daemon env, log-and-continue errors.
- `references/live-progress-jsonl-tap.md` — buffer-retaining stdout parse → progress reducer → deep-equal gated 100ms throttled notify.
- `references/session-rebind-sessionid-bridge.md` — session-id file bridge with spawned-subagent write skip; channel-scoped effective session id.
- `references/shutdown-unclaim-choreography.md` — own claims then spawned-agent claims released on leave; harness daemon deliberately survives sessions.
- `references/reservation-conflict-gate.md` — registration-embedded path patterns (dir-prefix vs exact), edit/write tool interception naming the holder.
- `references/status-computation-ladder.md` — active/idle/away/stuck cascade where holding work prevents away; auto-status precedence ladder.
- `references/activity-tracker-debounce-choreography.md` — per-path 5s edit debounce, single-flight 10s registry flush, 60s recent windows feeding auto-status.
- `references/agent-file-skills-inheritance.md` — frontmatter-or-whole-file agent defs, matched-pair YAML writer, skill-dir forwarding, 0o600 tmpfile prompts.
- `references/config-precedence-context-modes.md` — flat spread across settings→extension→project layers; contextMode forces context trio off in stages.
- `references/feed-scroll-window-math.md` — dual-coordinate scroll state (absolute window × bottom-relative offset) with hold-position-under-append arithmetic.
- `references/router-action-grammar.md` — group.op dispatch, param-rewriting aliases, loud tombstones for removed verbs, pre-registration allowlist.
- `references/send-to-feed-dead-agent-warning.md` — store-always/push-never delivery with terminal-spawn status warnings; unknown recipients never fail.
- `references/stalled-task-detection.md` — progress_log-last else claimed_at clocking with conservative no-clock exemption.
- `references/project-isolation-per-request-dirs.md` — per-request dir/config resolution via realpath'd cwd priority chain; dual isolation via dirs + cwd filter.
- `references/memorable-names-color-hashing.md` — themed AdjNoun minting, validation regex, Java-hash → truecolor palette assignment.
- `references/overlay-snapshot-notifications.md` — overlay close injects snapshot digest as triggerTurn message; completion cache dedupes alerts.
- `references/shell-alias-cli-resolution.md` — diff-gated PATH wrapper install; dist-first CLI resolution; `.git|.pi` ancestor walk capped at 20.
- `references/channel-listing-staleness-grammar.md` — #memory always-active exemption; named-by-recency vs session presence-over-feed classification.
- `references/task-spec-markdown-sidecar.md` — jsonl is truth, spec .md is disposable rendered data deleted before tombstone.
- `references/self-registration-synthesis.md` — buildSelfRegistration feeds ONE shared formatter for self and peer rows; loud no-channel throw.
- `references/join-flow-channel-inheritance.md` — save→register→conditional-restore triple for spawned channel inheritance; explicit flag beats hint.
- `references/swarm-board-aggregation.md` — heal-before-read board composition preserving history counts in empty state.
- `references/mention-autocomplete-input.md` — two-source deduped candidates, space-gated Tab cycling, `@all` channel-post sugar.
- `references/feed-sanitization-grammar.md` — inline-flatten vs newline-preserving preview policies applied on both write and read.
- `references/extension-lifecycle-hooks.md` — hook ownership map incl. reason-split double session_start and always-start-daemon rule.
- `references/overlay-render-cache-layout.md` — 50ms keyed frame cache tuned against the 100ms worker throttle; viewport-arithmetic panel heights.

## Capsule map
- **Channel & feed storage** — `unified-channel-jsonl-store`, `session-channel-allocation-ladder`, `feed-cache-stat-invalidation`, `feed-sanitization-grammar`, `channel-listing-staleness-grammar`: header-line JSONL format, collision-safe phrase ids, stat-pair caching, dual whitespace policies, per-kind staleness rules.
- **Registry & identity** — `registry-write-verify-claim`, `agents-cache-mtime-sync-bridge`, `memorable-names-color-hashing`, `self-registration-synthesis`: lockless name claims via pid round-trip, dual freshness caches, themed names + hashed colors, shared formatter rows.
- **Task engine** — `task-event-sourcing-replay`, `task-claim-guard-ladder`, `stale-claim-janitor-throttle`, `cascade-reset-dependency-sweep`, `stalled-task-detection`, `task-spec-markdown-sidecar`, `swarm-board-aggregation`: append-fold state machine with refusal taxonomy, janitorship, dependency cascades, stall clocks, spec sidecars, healed board views.
- **Subagent lifecycle** — `spawn-concurrency-task-binding-gates`, `spawned-agent-event-lifecycle`, `swarm-protocol-prompt-sandwich`, `agent-file-skills-inheritance`, `live-progress-jsonl-tap`, `shutdown-unclaim-choreography`: guarded spawning, restart-surviving event logs, contract prompts, persona files, stdout taps, parent-as-janitor exits.
- **Harness daemon & transport** — `harness-identity-resolution-ladder`, `harness-daemon-lifecycle`, `project-isolation-per-request-dirs`, `router-action-grammar`, `send-to-feed-dead-agent-warning`, `shell-alias-cli-resolution`: identity precedence, preserve-spawn restarts, per-project dirs, action grammar, feed-only delivery, PATH wrappers.
- **Host integration** — `session-rebind-sessionid-bridge`, `extension-lifecycle-hooks`, `join-flow-channel-inheritance`, `reservation-conflict-gate`, `status-computation-ladder`, `activity-tracker-debounce-choreography`, `config-precedence-context-modes`: session bridges, hook wiring, join choreography, reservations, presence math, activity debounces, config layers.
- **TUI overlay plane** — `feed-scroll-window-math`, `mention-autocomplete-input`, `overlay-snapshot-notifications`, `overlay-render-cache-layout`: scroll state machine, completion grammar, snapshot handoff, render budget.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Probe commands must be executed byte-exact from the repo root (`/mnt/hdd/utopia/inspo/external/ext-pi-messenger-swarm`) BEFORE pinning expected counts; test-title anchors are grepped once per suite. Next-pass targets: diff-first past `6fe429a` only; overlay render internals (render-detail/render-status/input keybinding tables) if an explicit porting question emerges; feed-window sparse-load tuning seams; swap deterministic probes for real vitest when a deps-installed clone exists.

## Provenance
pi-messenger-swarm (MIT), `main@6fe429a4b74ae276a621bb72910d7926fb6b3104` (= base_sha, zero drift, v0.25.24); Codebase Memory project `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm` (FULL mode, 2,493 nodes / 5,802 edges, gen 2026-08-24T03:33:39Z, generation_matches=true, parse_partial ×2 = tests/config.test.ts:9 + tests/swarm/agent-file-smoke.test.ts:13, neither cited; not_indexed ×5 = images by design; served spans verified against working tree pre-authoring; check_index_coverage stdin-JSON over all 18 core cited paths = no_recorded_issue + metadata_match). Pass-1 row-gap repair: repo had NO learning row before this squeeze. Runner BLOCKED honestly (no node_modules in inspo clone; vitest declared but not installed) — every Probe grep was executed byte-exact from repo root pre-write with counts corrected against live output (3 expectation fixes during execution), and all cited test titles were grep-verified exactly-once per suite (274 it() cases across 44 suites).

## Full view (memory graph)
Revalidate `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph root `/mnt/hdd/utopia/inspo/external/ext-pi-messenger-swarm`, branch main @ 6fe429a4, mode FULL, 2,493 nodes / 5,802 edges (14 labels; DEFINES 2,327 / CALLS 1,212 / USAGE 1,142 / IMPORTS 744 / SEMANTICALLY_RELATED+SIMILAR_TO 123), freshness gen 2026-08-24T03:33:39Z generation_matches=true at the pinned head. BM25 search_graph resolves Function/Method symbols line-exact (multi-symbol queries verified live rank-1); doc-shaped surfaces are minimal here so search_graph remains the working primitive — fall back to `search_code --pattern` only for README/yaml needles. Source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: unified JSONL channel format, event-sourced task fold, write-verify-claim registry, PID-liveness janitorship, cascade algorithm, identity ladder, scroll math, status cascade, prompt protocol clauses. Adapt host-specific integration: pi ExtensionAPI hooks, `@earendil-works/pi-tui` overlay rendering, the `pi --mode json` child invocation, shell-alias PATH injection, env-var names. Omit product behavior: the TUI visual design, emoji vocabularies, default thresholds (3 spawns / 10min stall / 900s stuck / 50-event retention) as sacred values, and the legacy global-mode path (`PI_MESSENGER_GLOBAL=1`) which exists only for backwards compatibility.

## Recovery (2026-09-02)
Re-indexed at the recorded pin in full mode: Codebase Memory project `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm` is ready (2493n/5802e, 0 skipped; parse_partial matches the capsule-documented caveat). Resolves the residual-backlog entry from the foundation-pack-migration work record.
