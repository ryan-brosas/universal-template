---
name: crewai-foundation
description: "Foundation leaf for crewAI's Flow runtime kernel: event-driven method graph execution, HITL pause/resume, checkpoint lineage, and the pluggable-infra patterns they share."
---

# crewAI: flow-runtime & event-bus foundation

## Use this for
Use when porting an event/listener workflow engine (or_ / and_ / router graphs), building pause-resume human-in-the-loop flows that survive process death, implementing append-only snapshot persistence or checkpoint lineage, or adding swappable process-wide backends (locks, storage) to a library. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/or-listener-fired-ledger.md` — fire-once semantics for multi-event `or_()` listeners plus trigger-scoped re-arm; boundary: cyclic re-fire clears the whole ledger.
- `references/racing-or-listeners-first-wins.md` — exclusive-event race groups run parallel, first success wins, losers cancelled; boundary: AND-nested events never race.
- `references/and-condition-pending-ledger.md` — per-listener event accumulators deleted on satisfaction; boundary: needs the OR ledger as its complement.
- `references/router-dispatch-loop.md` — routers drain sequentially, listeners fan out parallel, conditional starts re-enter cycles; boundary: falsy router outcome ends the arm silently.
- `references/listener-cycle-reentry.md` — call-count cap → resume-skip → cycle-discard tri-state gate; boundary: resume wins over cycle while the flag lives.
- `references/sync-method-thread-isolation.md` — copy_context + to_thread shim with returned-coroutine auto-await; boundary: copy must happen loop-side.
- `references/hook-pairing-exactly-once.md` — EXECUTION_START/END exactly-once pairing incl. HookAborted arms; boundary: latch flags before dispatch.
- `references/fork-vs-resume-state-identity.md` — fork re-stamps a fresh state.id, resume keeps it; boundary: missing fork source falls through silently.
- `references/sqlite-flow-state-ledger.md` — WAL + realpath-named lock + newest-row read; boundary: reads are deliberately lock-free.
- `references/persist-backend-precedence.md` — instance > method def > flow def > factory resolution cached by definition identity; boundary: enabled=False is a kill switch.
- `references/hitl-pause-resume-protocol.md` — persist-everything context, kickoff RETURNS the pending object, clear marker after completion; boundary: at-least-once step re-offer on crash.
- `references/feedback-outcome-collapse-ladder.md` — five-rung total collapse of free text to a declared outcome; boundary: every path returns outcomes[0] worst-case.
- `references/ask-timeout-executor-discipline.md` — abandon-don't-kill executor timeout over uncancellable providers; boundary: pre-wait auto-checkpoint.
- `references/event-scope-pairing.md` — ContextVar frame stack validating started/completed pairs; boundary: depth cap 100 converts leaks to errors.
- `references/replay-vs-emit-duality.md` — replay preserves ids and exposes is_replaying() for side-effect opt-out; boundary: timeline handlers must still process replays.
- `references/handler-dependency-levels.md` — Kahn levels + type-scoped plan cache with eager cycle rejection; boundary: sync handlers of one level share one job.
- `references/distributed-named-lock-backend.md` — md5-namespaced channels, Redis/file degradation, snapshot-on-entry backend swap; boundary: custom backends get raw names.
- `references/checkpoint-filename-lineage.md` — parent encoded in filename stem, resolve-prefix branch validation, per-branch prune; boundary: id = prefix before `_p-`.
- `references/auto-checkpoint-event-fanout.md` — subclass-tree bulk registration, sync-only dispatch, replay/lifecycle exclusion; boundary: dual registration double-writes.
- `references/checkpoint-version-migration.md` — migrate-inside-wrap-validator with structural-only inference; boundary: validate-before-migrate fails legacy data loudly.
- `references/flowmeta-field-triage.md` — metaclass annotation triage keeping fields, ClassVars, and methods distinct; boundary: parent-field collisions need frozen defaults.
- `references/state-id-guarantee-ladder.md` — exhaustive per-shape id stamping incl. StateWithId mixin and schema-marker class round-trip; boundary: dict states are copied before stamping.
- `references/wrapped-method-descriptor-binding.md` — bound-copy cloning with explicit attribute skip-set; boundary: losing unwrap() breaks Literal emit inference.
- `references/declarative-method-field-recovery.md` — recover methods absorbed into model_fields defaults (the `checkpoint` collision); boundary: namespace methods always win.
- `references/declarative-action-builder.md` — ordered isinstance registry over seven action kinds with reserved-kwarg local context; boundary: EachAction must stay first.
- `references/cel-template-interpolation.md` — lexer-driven `${...}` segment parsing preserving value types for single expressions; boundary: regex splitters mis-close nested braces.
- `references/event-bus-dual-plane-dispatch.md` — threadpool sync + dedicated-loop async dispatch with tracked futures; boundary: stream-chunk events bypass the executor.
- `references/writer-priority-rw-lock.md` — condition-variable counting RWLock protecting handler registries; boundary: notify_all on both release paths.
- `references/usage-aggregation-reentrancy.md` — outermost-owner latch, match-id filter, flush-before-detach; boundary: nested kickoffs never reset totals.
- `references/memory-drain-before-finished.md` — drain→flush→emit ordering with finally net; boundary: defer flag skips finish AND finalization together.
- `references/conditional-start-entry-ladder.md` — unconditional starts win, all-conditional flows promote every start; boundary: conditional starts never evaluate at t0.
- `references/human-feedback-outcome-split.md` — outcome routes while stashed real output lands in method_outputs; boundary: presence-in-dict handles None outputs.
- `references/persistence-factory-pluggable-default.md` — late-resolving global factory with documented multi-call contract; boundary: defaults must share durable state.
- `references/xrepo-processwide-backend-setter.md` — CROSS-REPO: set-once global + snapshot-on-use + graceful default trio (lock_store ≅ persistence factory).
- `references/xrepo-first-wins-racing.md` — CROSS-REPO vs langgraph: first-success-wins racing, cancel-after-victory, exceptions never win.
- `references/xrepo-appendonly-snapshot-ledger.md` — CROSS-REPO internal twin: SQLite rows and checkpoint filenames share the monotonic-token latest-wins contract.
- `references/xrepo-event-scope-pairing.md` — CROSS-REPO vs autogen: context-local start/end frames validated at pop time.
- `references/xrepo-pause-as-return-hitl.md` — CROSS-REPO vs agno/agency-swarm: pause is persisted data crossing an API boundary, never an escaped exception.
- `references/xrepo-copycontext-thread-hop.md` — CROSS-REPO vs agno: snapshot context/state BEFORE crossing any async/sync seam.

## Capsule map
- **Listener dispatch** — `or-listener-fired-ledger`: fire-once ledger + trigger-scoped re-arm for multi-event or_().
- **Listener dispatch** — `racing-or-listeners-first-wins`: exclusive alternatives race in parallel, first success cancels siblings.
- **Listener dispatch** — `and-condition-pending-ledger`: per-listener accumulators, delete-on-satisfy doubles as cycle re-arm.
- **Listener dispatch** — `router-dispatch-loop`: sequential router drain then parallel listener wave feeding conditional starts.
- **Listener dispatch** — `listener-cycle-reentry`: recursion cap, resume-skip, and full ledger reset for cyclic re-execution.
- **Method execution** — `sync-method-thread-isolation`: copy-context thread hop with coroutine auto-await.
- **Method execution** — `hook-pairing-exactly-once`: start/end interception pairs latched before dispatch.
- **State plane** — `fork-vs-resume-state-identity`: fresh id on fork, kept id on resume, silent fallback.
- **State plane** — `state-id-guarantee-ladder`: every initial-state shape terminates in a stamped id.
- **State plane** — `flowmeta-field-triage`: metaclass annotation triage with frozen-default collision handling.
- **State plane** — `wrapped-method-descriptor-binding`: descriptor cloning with skip-set preserving decorator payloads.
- **Persistence** — `sqlite-flow-state-ledger`: WAL, realpath locks, append-only newest-row read.
- **Persistence** — `persist-backend-precedence`: four-tier backend resolution cached by definition identity.
- **Persistence** — `persistence-factory-pluggable-default`: process-wide default factory, resolved late, shared-durable contract.
- **HITL** — `hitl-pause-resume-protocol`: serialize-everything pause, return-don't-raise, cross-process resume.
- **HITL** — `feedback-outcome-collapse-ladder`: total collapse ladder ending at outcomes[0].
- **HITL** — `ask-timeout-executor-discipline`: bounded input wait without orphaned-thread deadlock.
- **HITL** — `human-feedback-outcome-split`: outcome routing vs real output via presence-keyed stash.
- **Events bus** — `event-scope-pairing`: ContextVar frames validating started/completed linkage.
- **Events bus** — `replay-vs-emit-duality`: metadata-preserving replay with handler-visible flag.
- **Events bus** — `handler-dependency-levels`: topological handler levels, eager cycle rejection, plan caching.
- **Events bus** — `event-bus-dual-plane-dispatch`: snapshot-under-lock dual dispatch with tracked futures.
- **Events bus** — `writer-priority-rw-lock`: counting RWLock guarding registry snapshots.
- **Checkpoints** — `checkpoint-filename-lineage`: encoded-lineage filenames, branch traversal guard, per-branch prune.
- **Checkpoints** — `auto-checkpoint-event-fanout`: bulk subclass registration with replay exclusion.
- **Checkpoints** — `checkpoint-version-migration`: version-gated forward migrations inside wrap validators.
- **Declarative flows** — `declarative-method-field-recovery`: recovery sweep for pydantic-absorbed methods.
- **Declarative flows** — `declarative-action-builder`: ordered action registry with hidden local-context kwarg.
- **Declarative flows** — `cel-template-interpolation`: lexer-braced CEL segments, type-preserving single expressions.
- **Runtime plumbing** — `distributed-named-lock-backend`: hashed channels, env-degraded backends, snapshot dispatch.
- **Runtime plumbing** — `conditional-start-entry-ladder`: unconditional-fallback entry selection.
- **Runtime plumbing** — `usage-aggregation-reentrancy`: owner-latched token accumulation across nested kickoffs.
- **Runtime plumbing** — `memory-drain-before-finished`: ordering guarantee for post-finish memory visibility.
- **Cross-repo patterns** — `xrepo-processwide-backend-setter`, `xrepo-first-wins-racing`, `xrepo-appendonly-snapshot-ledger`, `xrepo-event-scope-pairing`, `xrepo-pause-as-return-hitl`, `xrepo-copycontext-thread-hop`.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question against project `ext-crewAI`. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Re-run probes byte-exact from the repo root (`/mnt/hdd/utopia/inspo/external/crewAI`, runner `.venv/bin/python -m pytest`) before shipping.

## Provenance
crewAI (MIT), `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory project `ext-crewAI` (353,322 nodes / 463,414 edges, status ready, head==base==pin 9e9a8577 after ff-pull of f4731f50→9e9a8577 and in-place refresh; content freshness proven by resolving drift-introduced `project_created_span` via search_code line-exact at lib/crewai-core/src/crewai_core/telemetry.py:411; parse_partial ×142 = versioned docs .mdx + CLI templates + viz assets, none cited).

## Full view (memory graph)
Revalidate `ext-crewAI` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph root `/mnt/hdd/utopia/inspo/external/crewAI`, branch main, pin 9e9a8577, FULL mode, generation_matches verified; coverage check stdin-JSON over 14 cited kernel paths returned no_recorded_issue + metadata_match ×14. BM25 search_graph is healthy on this corpus (unlike doc-shaped repos) but search_code resolves file-stem anchors line-exact when queries miss. Source and direct tests decide shipped claims.

## Boundaries
Adopt pure engine contracts (listener ledgers, pairing invariants, append-only snapshots, backend-setter pattern); adapt transport details (Redis/file locks, SQLite, CEL) to your host stack; omit product surfaces not mined here (Crew/Agent internals, tools catalog, enterprise Plus API, telemetry exporters, visualization assets).
