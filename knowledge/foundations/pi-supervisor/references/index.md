<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# pi-supervisor: agent supervision + steering foundation

## Use this for
Use when porting a supervisor/steering loop over an LLM coding agent — LLM-judged done/steer/continue decisions at settled checkpoints, deterministic mid-run stuck signals, algorithmic conversation compaction for judge context, ineffective-steering escalation tiers, session-entry state persistence across compaction/restart, model-locked tool activation, or live streaming-reasoning widgets. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./analyzer-error-bias.md` — idle failures nudge, working failures wait: the split fallback decision posture.
- `./builtin-judge-prompt-contract.md` — the built-in system prompt's five clauses and strict JSON response schema.
- `./cache-friendly-section-formatting.md` — stable-before-volatile section ordering, tail-capped transcript with header-boundary snap.
- `./causal-chain-turn-summaries.md` — marker-scan cause/resolution fragments with bounded sentinels and breadcrumb keys.
- `./commit-extraction.md` — pairing `git commit -m` calls with hashes recovered from following tool results.
- `./content-clipping-toolkit.md` — word/sentence boundary clipping primitives with surrogate-pair safety.
- `./decision-parsing-failsafe.md` — fence-tolerant decision parsing where every failure returns, none throw.
- `./decision-prompt-assembly.md` — outcome sandwich, IDLE-must-decide rule, scope-question policy, five-item cheating taxonomy.
- `./ephemeral-supervision-lifecycle.md` — supervision is ephemeral by contract: idle on any load-shaped event clears it.
- `./goal-inference-idle-kickstart.md` — throwaway-session goal extraction with kickstart only when the agent is idle.
- `./goal-preference-extraction.md` — goal substantiation filters, template truncation, scope-change capture, preference dedup.
- `./idle-nudge-fallback.md` — every analysis failure degrades to continue-or-nudge, never an exception out.
- `./ineffective-pattern-detection.md` — timestamp-based similarity over recent interventions plus a stagnation arm.
- `./in-memory-supervisor-session.md` — isolated in-memory session reuse keyed on model identity + system prompt.
- `./input-epoch-staleness-guard.md` — discarding decisions computed from a snapshot a user prompt has already superseded.
- `./last-used-model-sort-mirror.md` — mirroring another extension's persisted usage order inside your own picker.
- `./line-clear-animation-choreography.md` — delayed-done vs immediate-clear animation state machine.
- `./mid-run-signal-gate.md` — signal-triggered mid-run steering with the confidence bar and intervention-before-send ordering (alt: mid-run-signal-detection).
- `./model-locked-supervision.md` — model may start supervision once; only the user can change or stop it; goal-append grammar.
- `./normalize-filter-blocks.md` — message→block normalization, sanitization, thinking/noise/XML-wrapper stripping.
- `./outcome-inference.md` — quote-strip/length-cap normalization of inferred goals with null-on-failure arms.
- `./outstanding-context-extractor.md` — six prioritized blocker detectors with tsc-resolution tagging and an 8-item cap.
- `./session-entry-state-persistence.md` — appendEntry-per-mutation state store with reverse-walk load and tombstone stop.
- `./settled-gate-analysis-loop.md` — why agent_settled is the only trusted checkpoint and what happens on steer/done there.
- `./streaming-thinking-extractor.md` — pulling partial reasoning text out of a still-streaming JSON response.
- `./subagent-process-wait.md` — child-process census via ps with a bounded poll-and-proceed wait.
- `./supervisor-prompt-contract.md` — user-prompt assembly: agent status switching, reframe injection, intervention history display.
- `./tool-result-index.md` — one O(n) call→result look-ahead index replacing three independent forward scans.
- `./unified-symbol-extraction.md` — screen-reject + 15-regex declaration cascade producing file activity, symbol changes, type catalog in one pass.
- `./widget-action-renderer.md` — six-state status widget with width-aware truncation and thinking-line mirroring.
- `./workspace-config-store.md` — cwd/.pi config JSON with load/save cwd asymmetry and merge-preserving writes.
- `./asi-memory-loop.md` — free-form Actionable Side Information carried on interventions and summarized back into prompts.
- `./brief-transcript-compression.md` — stopword-budget truncation, bash semantic compression, twin collapse ladders, tail-keep caps.
- `./causal-marker-extraction.md` — marker-scan cause/resolution fragments with bounded sentinels and breadcrumb keys (alt: causal-chain-turn-summaries).
- `./commit-hash-pairing.md` — pairing `git commit -m` calls with hashes recovered from following tool results (alt: commit-extraction).
- `./compaction-survival-lifecycle.md` — persist-before-compaction, reload-after, willRetry guard, idle teardown.
- `./crash-resume-idle-teardown.md` — shared session-load handler that clears stale supervision when the agent is idle.
- `./fabric-provider-registration.md` — event-bus provider registration with re-register-on-discover and risk-tagged descriptors.
- `./goal-preference-extractors.md` — goal substantiation filters, template truncation, scope-change capture, preference dedup (alt: goal-preference-extraction).
- `./ineffective-pattern-detector.md` — timestamp-based similarity over the last 3 interventions plus a 60s stagnation arm.
- `./cache-friendly-formatting.md` — stable-before-volatile section ordering and tail-capped transcript with header-boundary snap (alt: cache-friendly-section-formatting).
- `./mid-run-signal-detection.md` — the deterministic predicates (error streaks, offset-keyed read loops) that interrupt a working agent.
- `./model-locked-tool-activation.md` — the start-only agent tool surface; model resolved only from the user-controlled ladder.
- `./model-selection-lastused-sort.md` — current-first → recency → provider → id comparator reading pi-model-sort's JSON with null fallback.
- `./normalize-filter-noise-frontstage.md` — six block kinds, sanitize inside normalize, thinking/noise-tool/XML-wrapper drops after (alt: normalize-filter-blocks).
- `./outstanding-context-resolution.md` — six ordered blocker arms over the last 25 blocks with tsc resolution by later same-file edit.
- `./reframe-tier-escalation.md` — 0–4 strategy ladder (directive/subgoal/pivot/minimal-slice) gated on detected ineffectiveness.
- `./reusable-supervisor-session.md` — singleton judge session reused while resolved model + system prompt match; in-memory, tools=[].
- `./safe-continue-decision-contract.md` — fence-tolerant decision parsing where every failure returns, none throw (alt: decision-parsing-failsafe).
- `./settled-checkpoint-steering.md` — epoch snapshot vs post-analysis comparison drops stale decisions unconditionally.
- `./streaming-reasoning-extraction.md` — "reasoning"-anchored escape-aware scan reads partial JSON streams live.
- `./subagent-liveness-gate.md` — ps-based child-pi detection fails open everywhere; timeout warns then proceeds.
- `./supervisor-md-override-ladder.md` — .pi/SUPERVISOR.md → ~/.pi/agent/SUPERVISOR.md → built-in whole-file replacement ladder.
- `./tool-result-lookahead-index.md` — one O(n) pre-scan pairs calls to results within a +3 window.
- `./unified-file-symbol-extraction.md` — created⊆modified dedup, symbols from edit payloads AND paired results, modified-first catalog caps.
- `./widget-action-state-machine.md` — timers killed on every entry; new thinking resets preserved lines; done waits CLEAR_DELAY_MS=15000 then animates lines away at 500ms.
## Capsule map
- **Supervision lifecycle** — `ephemeral-supervision-lifecycle`: supervision is ephemeral by contract; idle on ANY load-shaped event clears it, compaction keeps it only while working or retrying. · `session-entry-state-persistence`: append-only custom-entry journal (`supervisor-state`), reverse-scan-first-match = latest state, summarized-away = dead. · `model-locked-tool-activation`: start-only agent tool surface; model resolved from user-controlled ladder only. · `goal-inference-idle-kickstart`: inference needs history + empty active set; kickstart fires ONLY when idle, at all three entry points. · `subagent-liveness-gate`: ps-based child-pi detection fails open everywhere; timeout warns then proceeds.
- **Steering decisions** — `decision-prompt-assembly`: outcome stated first AND last, idle forbids continue, last-5 history with ASI dumps, pattern summary from ≥2× key frequency + suspicious-indicator scan. · `decision-parsing-failsafe`: fence→brace→raw triple extraction; ALL failures ⇒ continue@0; confidence default 0.5 gates mid-run steers. · `settled-checkpoint-steering`: epoch snapshot vs post-analysis comparison drops stale decisions unconditionally; steer='followUp', mid-run='steer'. · `analyzer-error-bias`: failure steers when idle (prevent hang), continues when working (wait for next checkpoint). · `ineffective-pattern-detection`: similarity run-length ≥2 OR stagnation ≥60s from `{interventions, startedAt}` alone. · `reframe-tier-escalation`: directive→subgoal→pivot→minimal-slice capped at 4, reset only on done/stop/new.
- **Judge infrastructure** — `reusable-supervisor-session`: singleton judge session reused while model identity + systemPrompt match; in-memory, tools=[], extension-less. · `supervisor-md-override-ladder`: `.pi/SUPERVISOR.md` → `~/.pi/agent/SUPERVISOR.md` → built-in; whole-file replacement, fresh load each analysis. · `builtin-judge-prompt-contract`: five clauses (idle mandate, speak-as-user, never-repeat, 5-pattern cheating prevention, ASI loop + strict schema). · `fabric-provider-registration`: eager emit + discovery-event re-register, version+callable shape-gate, risk-tagged descriptors.
- **Mid-run detection** — `mid-run-signal-detection`: ≥5 consecutive error results broken by any success; same-path+offset read loops ≥5 reset by edits; severity order tool_error > file_read_loop.
- **Compaction pipeline** — `normalize-filter-noise-frontstage`: six block kinds, sanitize inside normalize, thinking/noise-tools/XML-wrapper drops after. · `tool-result-lookahead-index`: one O(n) pre-scan pairs calls to results within +3. · `unified-file-symbol-extraction`: created⊆modified dedup, symbols from edit payloads AND paired results, DECL_SCREEN_RE quick-reject, modified-first catalog cap 12×8. · `outstanding-context-resolution`: six ordered arms over last-25 blocks, cap 8 items, tsc resolved by later same-file edit. · `brief-transcript-compression`: stopword-budget truncation, xN collapse, tail-keeping 8-cap with omission markers, 120-line header-aligned capBrief. · `causal-chain-turn-summaries`: marker lists most-specific-first, FRAGMENT_MAX=60/key=40, remnant verbs in KEY_STOPS. · `goal-preference-extraction`: LEADING_CHARS=200 paste defense, template-signal truncation, `[Scope change]` marker slot, one preference per block. · `cache-friendly-section-formatting`: stable sections first for prompt-cache prefix reuse; volatile + transcript last. · `content-clipping-toolkit`: clip word-boundary ≥60% + surrogate guard; clipSentence ≥50%; primitives never decorate. · `commit-extraction`: `-m` regex triple-quote forms, hash ladder bracket→range(new)→bare, `hash::message` dedup, keep last 8.
- **Live UI** — `streaming-reasoning-extraction`: `"reasoning"` anchor + `(?<!\\)"` terminator reads partial JSON streams; missing close = still streaming. · `widget-action-state-machine`: timers killed on every entry; new thinking resets preserved lines; done waits CLEAR_DELAY_MS=15000 then animates lines away at 500ms. · `model-selection-lastused-sort`: current-first → recency → provider → id comparator reading sibling extension's JSON with null fallback; save merges foreign keys.

- **Supervision lifecycle (sibling set)** — `ephemeral-supervision-lifecycle`, `session-entry-state-persistence`, `model-locked-tool-activation`, `goal-inference-idle-kickstart`, `subagent-liveness-gate`.
- **Steering decisions (sibling set)** — `decision-prompt-assembly`, `decision-parsing-failsafe`, `settled-checkpoint-steering`, `analyzer-error-bias`, `ineffective-pattern-detection`, `reframe-tier-escalation`.
- **Judge infrastructure (sibling set)** — `reusable-supervisor-session`, `supervisor-md-override-ladder`, `builtin-judge-prompt-contract`, `fabric-provider-registration`.
- **Mid-run detection (sibling set)** — `mid-run-signal-detection`.
- **Compaction pipeline (sibling set)** — `normalize-filter-noise-frontstage`, `tool-result-lookahead-index`, `unified-file-symbol-extraction`, `outstanding-context-resolution`, `brief-transcript-compression`, `causal-chain-turn-summaries`, `goal-preference-extraction`, `cache-friendly-section-formatting`, `content-clipping-toolkit`, `commit-extraction`.
- **Live UI (sibling set)** — `streaming-reasoning-extraction`, `widget-action-state-machine`, `model-selection-lastused-sort`.
- **Supervision loop kernel (lane set)** — `settled-gate-analysis-loop`: agent_settled is the only trusted checkpoint; steer records intervention before send; done resets counters and disposes. · `input-epoch-staleness-guard`: capture input epoch before analysis, compare after, drop stale decisions unconditionally. · `mid-run-signal-gate`: deterministic watchers decide WHEN (error streaks, read loops), the model decides WHAT at confidence ≥ 0.85; intervention recorded before send as 'steer'. · `idle-nudge-fallback` (+ `analyzer-error-bias` alt): failures become typed decisions — nudge when idle, continue when working, never throw.
- **State & survival (lane set)** — `session-entry-state-persistence`: appendEntry-per-mutation full snapshots with reverse-walk newest-wins load and tombstone stop. · `compaction-survival-lifecycle`: persist before compaction, reload after, never tear down when willRetry is pending. · `crash-resume-idle-teardown`: restored-active supervision is dropped when the agent is idle at any load-shaped event. · `model-locked-supervision` (+ `model-locked-tool-activation` alt): model may start but never modify or stop; user edits append ("Additionally: …"); tool schema omits model selection.
- **Steering intelligence (lane set)** — `reframe-tier-escalation`: 0–4 directive→subgoal→pivot→minimal-slice ladder, monotone within a goal, reset only on done/stop. · `ineffective-pattern-detector` (+ `ineffective-pattern-detection` alt): timestamps over turn counts; last-3 pairwise similarity via shared directive words + length ratio, or 60s stagnation from startedAt baseline. · `asi-memory-loop`: free-form ASI written by the model on every steer, aggregated by code (key frequency ≥2, suspicious-indicator sweep, verification-failure counts) back into prompts. · `supervisor-prompt-contract` (+ `decision-prompt-assembly`/`builtin-judge-prompt-contract` alts): outcome sandwich first+last, IDLE forbids continue, scope-question policy with secrets carve-out, five-item cheating taxonomy each paired to its verification move.
- **Goal inference (lane set)** — `outcome-inference` (+ `goal-inference-idle-kickstart` alt): throwaway session, quote-strip/newline-flatten/slice-200 normalization, null on every failure arm, kickstart only when idle.
- **Compaction pipeline (lane set)** — `normalize-filter-blocks` (+ `normalize-filter-noise-frontstage` alt): sanitize ANSI/CTRL inside normalize; thinking/noise-tools/XML-wrapper drops after. · `tool-result-index` (+ `tool-result-lookahead-index` alt): one O(n) pre-scan pairs calls to results within +3. · `unified-symbol-extraction` (+ `unified-file-symbol-extraction` alt): DECL_SCREEN_RE quick-reject then 15-regex cascade in one pass producing activity/symbols/catalog with Go uppercase-export rule. · `outstanding-context-extractor` (+ `outstanding-context-resolution` alt): six ordered arms over last-25 blocks, 8-item cap after tagging, [RESOLVED] rewrite by later same-file edit. · `brief-transcript-compression`: stopword-budget truncation, bash cd/pipe semantic compression, twin collapse ladders preserving (#ref) provenance, tail-keep caps. · `causal-marker-extraction` (+ `causal-chain-turn-summaries` alt): indexOf marker scan bounded FRAGMENT_MAX=60 sentinels, per-sentence fallback, file|resolution-key breadcrumbs. · `goal-preference-extractors` (+ `goal-preference-extraction` alt): LEADING_CHARS=200 paste defense, TEMPLATE_SIGNAL truncation, single [Scope change] slot, one preference per block. · `commit-hash-pairing` (+ `commit-extraction` alt): message from args, hash from following results bracketed → push-range-tail → bare hex, hash::message dedupe. · `cache-friendly-formatting` (+ `cache-friendly-section-formatting` alt): stable sections first for prompt-cache prefix reuse; header-snapped capBrief tail-keep 120.
- **Session client plane (lane set)** — `in-memory-supervisor-session` (+ `reusable-supervisor-session` alt): singleton judge session reused while resolved-model-object + systemPrompt match; in-memory, tools=[], extensions off. · `safe-continue-decision-contract` (+ `decision-parsing-failsafe` alt): fence→brace→raw extraction ladder, action enum gate, per-field defaults, reason-carrying typed continues. · `streaming-thinking-extractor` (+ `streaming-reasoning-extraction` alt): "reasoning"-anchored (?<!\\)" terminator reads partial JSON streams live.
- **Integration planes (lane set)** — `subagent-process-wait` (+ `subagent-liveness-gate` alt): direct-child ps census fails open; bounded poll-and-proceed warns then analyzes. · `fabric-provider-registration`: eager register emit + discovery-event re-register, version+callable shape gate, risk-tagged descriptors. · `workspace-config-store`: load reads process.cwd(), save takes explicit cwd; merge-preserving writes keep sibling keys.
- **UI plane (lane set)** — `widget-action-renderer` (+ `widget-action-state-machine` alt): six-state widget, snapshot capture at done transitions, ANSI-stripped width arithmetic. · `line-clear-animation-choreography`: immediate clear for steering/watching vs 15s hold then animate-away for done, timers preempted on every update. · `last-used-model-sort-mirror` (+ `model-selection-lastused-sort` alt): read-only mirror of pi-model-sort's persisted order re-applied after filtering; never writes global default.
## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
pi-supervisor (MIT), `master@92c0d6df986dfd138f941001e3fcc57a3ee07247` (v0.5.15); Codebase Memory project `mnt-hdd-utopia-inspo-external-ext-pi-supervisor` FULL mode 504n/1304e, generation 2026-08-24T03:33:44Z generation_matches=true, parse_partial ×0, skipped ×0; coverage stdin-JSON ×10 cited paths all no_recorded_issue + metadata_match.

## Full view (memory graph)
Revalidate `mnt-hdd-utopia-inspo-external-ext-pi-supervisor` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph is BM25 over symbol-bearing nodes (Function/Method/Interface rich; doc-shaped Section nodes sparse) — search_graph resolves every cited symbol line-exact; source and direct tests decide shipped claims.

## Boundaries
Adopt pure contracts: signal predicates, decision parser, tier algebra, compaction pipeline (pure functions over message arrays), clipping toolkit, epoch race gate. Adapt host-specific integration: pi ExtensionAPI event names, sendUserMessage delivery channels, sessionManager.getBranch entry journal, TUI widget registration, ps-based process detection. Omit product behavior: pi-fabric broker events unless you run a compatible bus, SUPERVISOR.md CLI plumbing details, media/screenshots, release tooling.

## Recovery (2026-09-02)
Re-indexed at the recorded pin in full mode: Codebase Memory project `mnt-hdd-utopia-inspo-external-ext-pi-supervisor` is ready (504n/1304e, 0 skipped; parse_partial matches the capsule-documented caveat). Resolves the residual-backlog entry from the foundation-pack-migration work record.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`analyzer-error-bias.md`](./analyzer-error-bias.md)
- [`asi-memory-loop.md`](./asi-memory-loop.md)
- [`brief-transcript-compression.md`](./brief-transcript-compression.md)
- [`builtin-judge-prompt-contract.md`](./builtin-judge-prompt-contract.md)
- [`cache-friendly-formatting.md`](./cache-friendly-formatting.md)
- [`cache-friendly-section-formatting.md`](./cache-friendly-section-formatting.md)
- [`causal-chain-turn-summaries.md`](./causal-chain-turn-summaries.md)
- [`causal-marker-extraction.md`](./causal-marker-extraction.md)
- [`commit-extraction.md`](./commit-extraction.md)
- [`commit-hash-pairing.md`](./commit-hash-pairing.md)
- [`compaction-survival-lifecycle.md`](./compaction-survival-lifecycle.md)
- [`content-clipping-toolkit.md`](./content-clipping-toolkit.md)
- [`crash-resume-idle-teardown.md`](./crash-resume-idle-teardown.md)
- [`decision-parsing-failsafe.md`](./decision-parsing-failsafe.md)
- [`decision-prompt-assembly.md`](./decision-prompt-assembly.md)
- [`ephemeral-supervision-lifecycle.md`](./ephemeral-supervision-lifecycle.md)
- [`fabric-provider-registration.md`](./fabric-provider-registration.md)
- [`goal-inference-idle-kickstart.md`](./goal-inference-idle-kickstart.md)
- [`goal-preference-extraction.md`](./goal-preference-extraction.md)
- [`goal-preference-extractors.md`](./goal-preference-extractors.md)
- [`idle-nudge-fallback.md`](./idle-nudge-fallback.md)
- [`in-memory-supervisor-session.md`](./in-memory-supervisor-session.md)
- [`ineffective-pattern-detection.md`](./ineffective-pattern-detection.md)
- [`ineffective-pattern-detector.md`](./ineffective-pattern-detector.md)
- [`input-epoch-staleness-guard.md`](./input-epoch-staleness-guard.md)
- [`last-used-model-sort-mirror.md`](./last-used-model-sort-mirror.md)
- [`line-clear-animation-choreography.md`](./line-clear-animation-choreography.md)
- [`mid-run-signal-detection.md`](./mid-run-signal-detection.md)
- [`mid-run-signal-gate.md`](./mid-run-signal-gate.md)
- [`model-locked-supervision.md`](./model-locked-supervision.md)
- [`model-locked-tool-activation.md`](./model-locked-tool-activation.md)
- [`model-selection-lastused-sort.md`](./model-selection-lastused-sort.md)
- [`normalize-filter-blocks.md`](./normalize-filter-blocks.md)
- [`normalize-filter-noise-frontstage.md`](./normalize-filter-noise-frontstage.md)
- [`outcome-inference.md`](./outcome-inference.md)
- [`outstanding-context-extractor.md`](./outstanding-context-extractor.md)
- [`outstanding-context-resolution.md`](./outstanding-context-resolution.md)
- [`reframe-tier-escalation.md`](./reframe-tier-escalation.md)
- [`reusable-supervisor-session.md`](./reusable-supervisor-session.md)
- [`safe-continue-decision-contract.md`](./safe-continue-decision-contract.md)
- [`session-entry-state-persistence.md`](./session-entry-state-persistence.md)
- [`settled-checkpoint-steering.md`](./settled-checkpoint-steering.md)
- [`settled-gate-analysis-loop.md`](./settled-gate-analysis-loop.md)
- [`streaming-reasoning-extraction.md`](./streaming-reasoning-extraction.md)
- [`streaming-thinking-extractor.md`](./streaming-thinking-extractor.md)
- [`subagent-liveness-gate.md`](./subagent-liveness-gate.md)
- [`subagent-process-wait.md`](./subagent-process-wait.md)
- [`supervisor-md-override-ladder.md`](./supervisor-md-override-ladder.md)
- [`supervisor-prompt-contract.md`](./supervisor-prompt-contract.md)
- [`tool-result-index.md`](./tool-result-index.md)
- [`tool-result-lookahead-index.md`](./tool-result-lookahead-index.md)
- [`unified-file-symbol-extraction.md`](./unified-file-symbol-extraction.md)
- [`unified-symbol-extraction.md`](./unified-symbol-extraction.md)
- [`widget-action-renderer.md`](./widget-action-renderer.md)
- [`widget-action-state-machine.md`](./widget-action-state-machine.md)
- [`workspace-config-store.md`](./workspace-config-store.md)
