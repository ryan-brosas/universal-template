---
name: billion-context-pi-foundation
description: "Use when building long-context agent delegation and context management: per-turn context transforms, message-range compression, async subagent delegation, watchdogs, tool guardrails."
disable-model-invocation: true
---

# Billion-Context-Pi Foundation

## Use this for
Use when building long-context agent context management (compress/decompress/search over conversation history), async subagent spawning with guaranteed termination, or any pi/omp-style extension that must rewrite LLM-bound context every turn. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/context-transform-spine.md` — the per-LLM-call transform pipeline: lock → load → processTurn → save → rebuild → nudge inject.
- `references/sent-view-arbitration.md` — which token number drives decisions: the calibrated sent view, not the host's tree-scale usage (false-emergency guard).
- `references/density-calibration.md` — per-model chars→token density learned from provider usage: cumulative anchors, ±20% two-round confirmation, raw-basis feedback trap.
- `references/overflow-selfheal-ladder.md` — context-overflow 400 → learn the real window → arm an emergency → next turn re-centers below it; never retry an overflow.
- `references/throttle-retry-hybrid.md` — provider 429 → native rewrite for fast probes + budgeted sentinel kick for long waits; triple-guard classifier; load-bearing error string.
- `references/ref-tag-roundtrip.md` — mNNNNN refs injected LLM-only; assistant no-tag rule; kernel-body-wins rebuild.
- `references/sequence-unique-alignment.md` — suffix-array unique-longest-run alignment between persisted and live lists, refusing ANY ambiguity across sources.
- `references/message-projection-normalizer.md` — session entries → CoreMessages role ladder incl. the thinking-only-drop that prevents provider 400s.
- `references/dual-host-session-reconciliation.md` — capability-detected host merge when the session log lags event.messages.
- `references/session-state-mutex.md` — promise-chain per-session mutex + atomic session-file state with forward-compat merges.
- `references/compress-decompress-contract.md` — range compression with partial-success batches; file-first restoration under a path jail.
- `references/compressed-only-search-index.md` — search corpus = block-covered messages only; earliest-block ownership; your state owns visibility truth.
- `references/status-parity-reporting.md` — status views must run the production transform so reports match what the model receives.
- `references/compress-retry-breaker.md` — failed-compress re-prompt ledger: turn-scoped, toolCallId-deduped, capped at 3, cap suppresses even emergency nudges while truncation stays mechanical.
- `references/exactly-once-delegate-delivery.md` — waiter XOR injection with late-wait pointer dedup across three racing delivery paths.
- `references/child-spawn-mechanics.md` — env depth gate, stdin task delivery, soft --tools allowlist, async→sync downgrade on one-shot hosts.
- `references/watchdog-four-timers.md` — idle/hard/EOF-grace/TERM→KILL timers DURING the run plus settledGrace teardown kill AFTER it; settled re-check before every signal; unref everything.
- `references/watchdog-settled-grace.md` — the fifth timer: agent_settled fired but process alive past grace ⇒ kill, idempotent arming, clear-before-kill ordering.
- `references/json-event-child-parsing.md` — newline-delimited child events converging to exact reply text under four stream shapes.
- `references/tool-result-guardrails.md` — call-site timeout injection + byte-safe output capping with recovery-path notices.
- `references/subagent-tools-injection.md` — detect another package's install tier, discover its agents' frontmatter, merge capability tools base-wins into user overrides with backup/mtime/tmp+rename/verify-or-restore (supersedes the old settings-self-patcher contract).
- `references/commands-surface.md` — five thin slash commands over one runtime; status panel keeps host-footer scale and sent-view estimate apart (never subtract cross-scale); provider-reported-only cache averaging.
- `references/throttled-auto-update.md` — self-update guarded by opt-out ladder, in-flight flag, pre-write throttle stamp, semver+execFile-array install.
- `references/config-precedence-ladder.md` — env > adapter > live window > fallback; user JSON wins except kernel-safety keys.
- `references/fleet-widget-lifecycle.md` — render-key debounce, idle self-stop, direct mode guard, double best-effort teardown.
- `references/system-prompt-doctrine.md` — tag hygiene, summaries-as-historical, blocking-wait-not-polling, untrusted-notification framing.
- `references/event-applier-delta-ledger.md` — reply-delta ledger + text_end tail backfill; shorter-than-deltas keeps the file and warns.
- `references/activity-stream-two-sinks.md` — human activity file vs machine reply file; accumulated-snapshot tool updates deduped via prefix slice.
- `references/delegate-run-lifecycle.md` — running/completed/failed/cancelled over the shared runs Map; cancelled = terminal-without-result; settled latch.
- `references/sync-delegate-collection.md` — never-rejecting waitForChild, stderr-on-failure body selection, always-persist-plus-pointer.
- `references/extension-bootstrap-wiring.md` — cancel host compaction first, session lifecycle order, per-call vs startup duties, custom_message mirror.
- `references/nudge-injection-channels.md` — append-per-rebuild nudge, last-user-message turn key, emergency ≥80% dedup bypass, retry-cap override, viableRanges pre-filter, debug terminal echo.
- `references/token-accounting-exclusions.md` — estimate skips compress calls + covered ids; active-block-only coverage; decisions run on the calibrated sent view (see sent-view-arbitration).
- `references/search-result-action-rendering.md` — every hit carries its decompress command; visible-in-context statement; census on empty results.
- `references/fail-silent-file-logging.md` — per-step swallowed I/O, always-on errors, opt-in debug, rename rotation before append.
- `references/host-boundary-compat-normalization.md` — string-vs-array system-prompt divergence normalized at exactly two boundary points.
- `references/proxy-self-disable-gate.md` — truthy-env bail-out as the FIRST statement of the extension factory when a sibling plugin owns your tool names (no runtime construction under the gate).
- `references/stable-tag-token-rerender.md` — `tokens=` in injected ref tags recomputed RAW from the exact body ridden every rebuild; density-independent, ref/type preserved.
- `references/footer-status-dedupe.md` — 500ms-tick status line that diffs rendered text before touching the host API, treats cleared-state as first-class in the diff, and best-effort-catches teardown.
- `references/e2e-fake-llm-server.md` — pure-Node OpenAI-compatible SSE stub: file-backed turn counter across CLI invocations, auxiliary-request bypass, ref/nudge parsing into compress ranges, per-request observations file.
- `references/e2e-runner-isolation.md` — per-scenario isolated HOME (both HOME+USERPROFILE), fake-provider models.json, one real `pi -p` per non-auto turn, spawnSync health-probe bridge, newest-mtime state selection.
- `references/e2e-verifier-vocabulary.md` — post-run assertions over the persisted CompressionState alone: active-block covered-id union, nudge baseline arithmetic, observation-derived limits, session-log tool scan.

## Capsule map
- **Context engine** — `context-transform-spine`, `session-state-mutex`, `sent-view-arbitration`, `density-calibration`: the locked read-transform-save loop over per-session compression state, its atomic persistence contract, and the calibrated sent-view scale every decision runs on.
- **Message plane** — `message-projection-normalizer`, `ref-tag-roundtrip`, `stable-tag-token-rerender`, `dual-host-session-reconciliation`, `sequence-unique-alignment`: entries → CoreMessages → tagged LLM array with raw recomputed size annotations, stable ids preserved across hosts whose logs lag differently, aligned only when uniquely matchable.
- **Compression & retrieval** — `compress-decompress-contract`, `compressed-only-search-index`, `status-parity-reporting`: range compression with addressable trails, covered-only search, transform-parity status views.
- **Delegation** — `exactly-once-delegate-delivery`, `child-spawn-mechanics`, `watchdog-four-timers`, `json-event-child-parsing`: spawn bounded children, deliver results exactly once, guarantee death, parse their streams losslessly.
- **Watchdog post-settle** — `watchdog-settled-grace`: bound teardown hangs after agent_settled without racing normal exits.
- **Delegate runtime planes** — `event-applier-delta-ledger`, `activity-stream-two-sinks`, `delegate-run-lifecycle`, `sync-delegate-collection`: stream the child's reply without loss or duplication, render its progress for humans, settle every run through a four-state machine, and collect blocking runs without ever rejecting.
- **Integration & policy** — `extension-bootstrap-wiring`, `nudge-injection-channels`, `token-accounting-exclusions`: wire the extension lifecycle (compaction cancel first), inject compression nudges once per turn with an emergency bypass, and keep token estimates honest via exclusions.
- **Coexistence & display** — `proxy-self-disable-gate`, `footer-status-dedupe`: step aside cleanly when a sibling plugin owns your tool names, and render live status lines without churning the host UI.
- **Failure recovery & throttling** — `throttle-retry-hybrid`, `overflow-selfheal-ladder`, `compress-retry-breaker`: classify provider failures correctly (throttle vs overflow vs quota — each recovers through a different channel), and keep model-driven compression from looping when its attempts fail.
- **Tool & infra surfaces** — `search-result-action-rendering`, `fail-silent-file-logging`, `host-boundary-compat-normalization`: self-describing search results, a logger that can never crash the host, and host string/array divergence quarantined at boundaries.
- **Guardrails & ops** — `tool-result-guardrails`, `subagent-tools-injection`, `throttled-auto-update`, `config-precedence-ladder`: bash timeout/output caps, safe cross-package config patching (detect→discover→base-wins merge→atomic write ladder), guarded self-update, layered config resolution.
- **Command surface** — `commands-surface`: thin slash commands over the runtime; the human status panel runs the production transform and keeps two token scales strictly apart.
- **Presentation & doctrine** — `fleet-widget-lifecycle`, `system-prompt-doctrine`: cheap live UI for background work; the prompt clauses that make tools used correctly.
- **E2E harness** — `e2e-fake-llm-server`, `e2e-runner-isolation`, `e2e-verifier-vocabulary`: full-pipeline regression that drives the REAL host headlessly against a scripted fake LLM and asserts on persisted state files.

## Extending the foundation
Add one `references/<seam>.md` capsule-v2 for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Sweep order for future passes: diff-first past `6a88c556` with a citation-vs-inventory grep against ALL refs (pass 7 wired the subagent-injection rewrite + e2e harness capsules; pass 8 added commands-surface and re-anchored exactly-once + watchdog-four-timers). Remaining thin spots for a future pass: PROVENANCE SWEEP — ~28 older capsules still cite pre-6a88c556 pins and dead/stale graph-project names (`billion-context-pi`, `mnt-hdd-utopia-inspo-coding-agents-billion-context-pi`) in their Source lines and Retrieve blocks; refresh each against the twin project only with an independent per-capsule source check (no bulk rewrite), starting with the delegate-plane set (delegate-run-lifecycle, sync-delegate-collection, json-event-child-parsing, event-applier-delta-ledger, activity-stream-two-sinks, watchdog-settled-grace) whose delegate-tool.ts anchors moved when buildChildArgs was extracted; then messages.ts/tag-tokens.ts inner seams if any remain uncited.

## Provenance
billion-context-pi (MIT), `master@6a88c5565355baebccfaf27398a6008fe08619ed`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi` (1,559 nodes / 4,000 edges, full mode, head==base==pin, zero parse_partial/skipped; generation 2026-08-25T07:58:00Z). STALE-TWIN NOTE: short-name project `billion-context-pi` remains STUCK at the pre-drift graph (783n/2,014e @558a83a9) and the older path-slugged twin `mnt-hdd-utopia-inspo-coding-agents-billion-context-pi` is GONE from list_projects — every Retrieve block and this Provenance cite the current twin. Pass-8 RE-ENTRY (2026-08-26, miner-billion-context-pi lane): pin unchanged; twin verified ready via index_status (head==base==6a88c556); upstream suite 414/414 GREEN executed at this pin; commands-surface capsule added; exactly-once-delegate-delivery + watchdog-four-timers re-anchored to source-exact lines (runs :181, finalize :782-853, injectedWaitMessage :470-479; attachWatchdogs :43-125); settings-self-patcher retired as superseded. Pass-7 history: setup-subagent-tools f30363d rewrite + e2e harness capsules mined; pass-5: pin advanced 1c87eb50→6a88c556, twin re-indexed in place; pass-4: 558a83a9→1c87eb50 (+186 commits), suite 414/414 GREEN after correcting a stale acp-kernel install to the lockfile-required 0.0.44.

## Full view (memory graph)
Revalidate `mnt-hdd-utopia-inspo-billion-context-pi` before porting (the short-name project serves a stuck pre-drift graph and the `coding-agents` slug no longer exists): run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the transform spine, exactly-once delivery, five-timer watchdog (incl. settledGrace), ref-tag round-trip, unique-alignment refusal discipline, and the settings/auto-update safety ladders — these are host-portable contracts pinned by direct tests. Also adopt: the env-gated self-disable factory gate (bail before ANY side effect when a sibling plugin owns your tool names), raw-count stable re-rendering of injected size tags (density-independent, body-derived), text-diffed timer status lines with cleared-state-as-first-class dedupe, the runtime planes: delta-ledger reply applier, cancelled-as-terminal-no-result lifecycle, stderr-on-failure sync collection, compaction-cancelling bootstrap order, per-turn nudge keying with emergency bypass AND retry-cap override, calibrated sent-view token truth (never let tree-scale host usage drive decisions), density calibration fed RAW estimates only, the throttle-vs-overflow classifier split with learn-window-and-arm self-heal, the turn-scoped compress-retry breaker, honest token-exclusion accounting, self-describing search results, fail-silent logging, and boundary-quarantined host compat. Adapt host event names, CLI flags, config paths, and prompt voice to your platform. Omit acp-kernel internals (imported dependency), pi/omp product surfaces (TUI kit, session manager), and the builtin-role allowlist tables (data, not contract).
