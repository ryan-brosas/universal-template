<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# crewAI: flow-runtime & event-bus foundation

## Use this for
Use when porting an event/listener workflow engine (or_ / and_ / router graphs), building pause-resume human-in-the-loop flows that survive process death, implementing append-only snapshot persistence or checkpoint lineage, or adding swappable process-wide backends (locks, storage) to a library. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./or-listener-fired-ledger.md` — fire-once semantics for multi-event `or_()` listeners plus trigger-scoped re-arm; boundary: cyclic re-fire clears the whole ledger.
- `./racing-or-listeners-first-wins.md` — exclusive-event race groups run parallel, first success wins, losers cancelled; boundary: AND-nested events never race.
- `./and-condition-pending-ledger.md` — per-listener event accumulators deleted on satisfaction; boundary: needs the OR ledger as its complement.
- `./router-dispatch-loop.md` — routers drain sequentially, listeners fan out parallel, conditional starts re-enter cycles; boundary: falsy router outcome ends the arm silently.
- `./listener-cycle-reentry.md` — call-count cap → resume-skip → cycle-discard tri-state gate; boundary: resume wins over cycle while the flag lives.
- `./sync-method-thread-isolation.md` — copy_context + to_thread shim with returned-coroutine auto-await; boundary: copy must happen loop-side.
- `./hook-pairing-exactly-once.md` — EXECUTION_START/END exactly-once pairing incl. HookAborted arms; boundary: latch flags before dispatch.
- `./fork-vs-resume-state-identity.md` — fork re-stamps a fresh state.id, resume keeps it; boundary: missing fork source falls through silently.
- `./sqlite-flow-state-ledger.md` — WAL + realpath-named lock + newest-row read; boundary: reads are deliberately lock-free.
- `./persist-backend-precedence.md` — instance > method def > flow def > factory resolution cached by definition identity; boundary: enabled=False is a kill switch.
- `./hitl-pause-resume-protocol.md` — persist-everything context, kickoff RETURNS the pending object, clear marker after completion; boundary: at-least-once step re-offer on crash.
- `./feedback-outcome-collapse-ladder.md` — five-rung total collapse of free text to a declared outcome; boundary: every path returns outcomes[0] worst-case.
- `./ask-timeout-executor-discipline.md` — abandon-don't-kill executor timeout over uncancellable providers; boundary: pre-wait auto-checkpoint.
- `./event-scope-pairing.md` — ContextVar frame stack validating started/completed pairs; boundary: depth cap 100 converts leaks to errors.
- `./replay-vs-emit-duality.md` — replay preserves ids and exposes is_replaying() for side-effect opt-out; boundary: timeline handlers must still process replays.
- `./handler-dependency-levels.md` — Kahn levels + type-scoped plan cache with eager cycle rejection; boundary: sync handlers of one level share one job.
- `./distributed-named-lock-backend.md` — md5-namespaced channels, Redis/file degradation, snapshot-on-entry backend swap; boundary: custom backends get raw names.
- `./checkpoint-filename-lineage.md` — parent encoded in filename stem, resolve-prefix branch validation, per-branch prune; boundary: id = prefix before `_p-`.
- `./auto-checkpoint-event-fanout.md` — subclass-tree bulk registration, sync-only dispatch, replay/lifecycle exclusion; boundary: dual registration double-writes.
- `./checkpoint-version-migration.md` — migrate-inside-wrap-validator with structural-only inference; boundary: validate-before-migrate fails legacy data loudly.
- `./flowmeta-field-triage.md` — metaclass annotation triage keeping fields, ClassVars, and methods distinct; boundary: parent-field collisions need frozen defaults.
- `./state-id-guarantee-ladder.md` — exhaustive per-shape id stamping incl. StateWithId mixin and schema-marker class round-trip; boundary: dict states are copied before stamping.
- `./wrapped-method-descriptor-binding.md` — bound-copy cloning with explicit attribute skip-set; boundary: losing unwrap() breaks Literal emit inference.
- `./declarative-method-field-recovery.md` — recover methods absorbed into model_fields defaults (the `checkpoint` collision); boundary: namespace methods always win.
- `./declarative-action-builder.md` — ordered isinstance registry over seven action kinds with reserved-kwarg local context; boundary: EachAction must stay first.
- `./cel-template-interpolation.md` — lexer-driven `${...}` segment parsing preserving value types for single expressions; boundary: regex splitters mis-close nested braces.
- `./event-bus-dual-plane-dispatch.md` — threadpool sync + dedicated-loop async dispatch with tracked futures; boundary: stream-chunk events bypass the executor.
- `./writer-priority-rw-lock.md` — condition-variable counting RWLock protecting handler registries; boundary: notify_all on both release paths.
- `./usage-aggregation-reentrancy.md` — outermost-owner latch, match-id filter, flush-before-detach; boundary: nested kickoffs never reset totals.
- `./memory-drain-before-finished.md` — drain→flush→emit ordering with finally net; boundary: defer flag skips finish AND finalization together.
- `./conditional-start-entry-ladder.md` — unconditional starts win, all-conditional flows promote every start; boundary: conditional starts never evaluate at t0.
- `./human-feedback-outcome-split.md` — outcome routes while stashed real output lands in method_outputs; boundary: presence-in-dict handles None outputs.
- `./persistence-factory-pluggable-default.md` — late-resolving global factory with documented multi-call contract; boundary: defaults must share durable state.
- `./xrepo-processwide-backend-setter.md` — CROSS-REPO: set-once global + snapshot-on-use + graceful default trio (lock_store ≅ persistence factory).
- `./xrepo-first-wins-racing.md` — CROSS-REPO vs langgraph: first-success-wins racing, cancel-after-victory, exceptions never win.
- `./xrepo-appendonly-snapshot-ledger.md` — CROSS-REPO internal twin: SQLite rows and checkpoint filenames share the monotonic-token latest-wins contract.
- `./xrepo-event-scope-pairing.md` — CROSS-REPO vs autogen: context-local start/end frames validated at pop time.
- `./xrepo-pause-as-return-hitl.md` — CROSS-REPO vs agno/agency-swarm: pause is persisted data crossing an API boundary, never an escaped exception.
- `./xrepo-copycontext-thread-hop.md` — CROSS-REPO vs agno: snapshot context/state BEFORE crossing any async/sync seam.
- `./flow-runtime-dag-engine.md` — how do @start/@listen/@router methods become an executed DAG with cyclic re-entry and resume?
- `./flow-engine-loop-safety.md` — how does the event runtime bound infinite listener cycles and dedupe or_() triggers?
- `./or-listener-fire-once-rearm-racing.md` — fire-once latch, router-loop re-arm, and first-wins racing for multi-event or() listeners.
- `./flow-hooks-ladder.md` — EXECUTION_START/INPUT/PRE_STEP/POST_STEP/OUTPUT/EXECUTION_END interception ladder with payload rewrite.
- `./flow-kickoff-dual-mode-entry.md` — nested-loop escape, restore/fork, and the exactly-once failure pairing ladder.
- `./flow-ask-blocking-input.md` — contextvar-named steps, auto-checkpoint before blocking, timeout-None contract.
- `./plan-execute-flow-graph.md` — how do @start/@router labels wire a supervisor loop that cannot fall through?
- `./sqlite-flow-persistence.md` — append-only snapshots, latest-row restore, and the cross-process file lock.
- `./checkpoint-config-coercion.md` — True→config BeforeValidator with handler-registration side effect.
- `./human-feedback-pause-resume.md` — exception-as-control-flow with persisted pending context.
- `./human-feedback-rerun.md` — how does feedback loop the WHOLE flow while preserving conversation, and skip re-planning?
- `./crew-kickoff-scheduling.md` — how does the crew-level engine order tasks, fan out async ones, and clean up?
- `./crew-task-pipeline.md` — async-fence batching, conditional-task barrier, and replay-aware start index.
- `./task-agent-handoff.md` — how does a Task drive the executor, collect tool failures, and apply guardrails?
- `./todo-dependency-scheduler.md` — when do steps run sequentially vs in parallel, and what unblocks a failed dependency?
- `./deterministic-fingerprints.md` — uuid5-seeded stable IDs for agents/crews/tasks.
- `./executor-flow-state.md` — how does one AgentExecutor instance reset between runs without losing its identity?
- `./step-executor-worker.md` — how does one plan step run in isolation with its own multi-turn tool loop and no shared state?
- `./react-parser.md` — how is free LLM text turned into Action/Finish, and what does json_repair fix without inventing data?
- `./finalize-synthesis.md` — how does the run end with a guaranteed AgentFinish even when no LLM ever produced one?
- `./context-recovery-ladder.md` — how does the executor survive context-length errors, and what does summarization preserve?
- `./reasoning-effort-ladder.md` — how much observation/replan machinery runs per step at low/medium/high?
- `./replan-machinery.md` — when does the plan regenerate, what does it preserve, and why is the counter incremented by the caller?
- `./planning-llm-contract.md` — how is the initial plan produced, refined until "ready", and kept out of task descriptions?
- `./planner-observation-parsing.md` — how are four different LLM response shapes coerced into one StepObservation without silent defaults?
- `./rpm-and-force-finish.md` — how are provider rate limits and runaway loops bounded?
- `./provider-tool-call-normalization.md` — how do five LLM provider shapes collapse into one (call_id, name, args) tuple?
- `./llm-stop-param-recovery.md` — string-sniffed capability ladder with persistent drop_params memory for unsupported 'stop'.
- `./prompt-cache-breakpoints.md` — where are cache_control markers placed so ReAct loops hit the provider prompt cache?
- `./native-tool-batch.md` — when do parallel calls run, and how do result_as_answer and failures short-circuit?
- `./multimodal-file-injection.md` — how do crew/task files and inputs reach the model as real attachments on the last user message?
- `./stream-frame-pipeline.md` — contextvar sinks, channel taxonomy, and thread-bridge generators.
- `./tool-cache-and-limits.md` — when is a repeated tool call served from cache, and how is a per-tool call budget enforced?
- `./tool-cache-opt-in.md` — crew-level cache handler offered to agents, default re-execution.
- `./tool-failure-protocol.md` — run-but-failed tools with policy ladder.
- `./tool-failure-taxonomy.md` — how does a tool say "I ran but failed", and what do ignore/warn/raise mean at each call site?
- `./state-copy-discipline.md` — deep-copy-with-fallback for unpickleable objects and model-construct rescue.
- `./event-bus-dispatch.md` — background-loop emit, future tracking, stream-chunk sync bypass, and replay-without-mutation.
- `./event-handler-dependency-graph.md` — Kahn levels with cached execution plans and aemit bypass.
- `./usage-aggregation-ownership.md` — reentrant-safe listener attach/detach around kickoff ownership.

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
- **Flow runtime** — `flow-runtime-dag-engine`: @start/@listen/@router methods become an executed DAG with cyclic re-entry and resume.
- **Flow runtime** — `flow-engine-loop-safety`: bounds infinite listener cycles and dedupes or_() triggers.
- **Flow runtime** — `or-listener-fire-once-rearm-racing`: fire-once latch, router-loop re-arm, first-wins racing for multi-event or() listeners.
- **Flow runtime** — `flow-hooks-ladder`: EXECUTION_START/INPUT/PRE_STEP/POST_STEP/OUTPUT/EXECUTION_END interception with payload rewrite.
- **Flow runtime** — `flow-kickoff-dual-mode-entry`: nested-loop escape, restore/fork, exactly-once failure pairing ladder.
- **Flow runtime** — `flow-ask-blocking-input`: contextvar-named steps, auto-checkpoint before blocking, timeout-None contract.
- **Flow runtime** — `plan-execute-flow-graph`: @start/@router labels wire a supervisor loop that cannot fall through.
- **Flow persistence & HITL** — `sqlite-flow-persistence`: append-only snapshots, latest-row restore, cross-process file lock.
- **Flow persistence & HITL** — `checkpoint-config-coercion`: True→config BeforeValidator with handler-registration side effect.
- **Flow persistence & HITL** — `human-feedback-pause-resume`: exception-as-control-flow with persisted pending context.
- **Flow persistence & HITL** — `human-feedback-rerun`: feedback loops the WHOLE flow while preserving conversation, skips re-planning.
- **Crew engine** — `crew-kickoff-scheduling`: crew-level task ordering, async fan-out, cleanup.
- **Crew engine** — `crew-task-pipeline`: async-fence batching, conditional-task barrier, replay-aware start index.
- **Crew engine** — `task-agent-handoff`: a Task drives the executor, collects tool failures, applies guardrails.
- **Crew engine** — `todo-dependency-scheduler`: sequential-vs-parallel step scheduling; what unblocks a failed dependency.
- **Crew engine** — `deterministic-fingerprints`: uuid5-seeded stable IDs for agents/crews/tasks.
- **Executor & ReAct loop** — `executor-flow-state`: one AgentExecutor instance resets between runs without losing its identity.
- **Executor & ReAct loop** — `step-executor-worker`: one plan step runs in isolation with its own multi-turn tool loop and no shared state.
- **Executor & ReAct loop** — `react-parser`: free LLM text → Action/Finish; json_repair fixes without inventing data.
- **Executor & ReAct loop** — `finalize-synthesis`: the run ends with a guaranteed AgentFinish even when no LLM ever produced one.
- **Executor & ReAct loop** — `context-recovery-ladder`: surviving context-length errors; what summarization preserves.
- **Executor & ReAct loop** — `reasoning-effort-ladder`: how much observation/replan machinery runs per step at low/medium/high.
- **Executor & ReAct loop** — `replan-machinery`: when the plan regenerates, what it preserves, caller-incremented counter.
- **Executor & ReAct loop** — `planning-llm-contract`: initial plan produced, refined until "ready", kept out of task descriptions.
- **Executor & ReAct loop** — `planner-observation-parsing`: four LLM response shapes coerced into one StepObservation without silent defaults.
- **Executor & ReAct loop** — `rpm-and-force-finish`: provider rate limits and runaway loops bounded.
- **LLM/provider plane** — `provider-tool-call-normalization`: five LLM provider shapes collapse into one (call_id, name, args) tuple.
- **LLM/provider plane** — `llm-stop-param-recovery`: string-sniffed capability ladder with persistent drop_params memory for unsupported 'stop'.
- **LLM/provider plane** — `prompt-cache-breakpoints`: cache_control marker placement so ReAct loops hit the provider prompt cache.
- **LLM/provider plane** — `native-tool-batch`: when parallel calls run; result_as_answer and failure short-circuits.
- **LLM/provider plane** — `multimodal-file-injection`: crew/task files and inputs reach the model as real attachments on the last user message.
- **LLM/provider plane** — `stream-frame-pipeline`: contextvar sinks, channel taxonomy, thread-bridge generators.
- **Tools & state** — `tool-cache-and-limits`: when repeated tool calls are served from cache; per-tool call budget enforcement.
- **Tools & state** — `tool-cache-opt-in`: crew-level cache handler offered to agents, default re-execution.
- **Tools & state** — `tool-failure-protocol`: run-but-failed tools with policy ladder.
- **Tools & state** — `tool-failure-taxonomy`: how a tool says "I ran but failed"; ignore/warn/raise at each call site.
- **Tools & state** — `state-copy-discipline`: deep-copy-with-fallback for unpickleable objects and model-construct rescue.
- **Event bus & usage** — `event-bus-dispatch`: background-loop emit, future tracking, stream-chunk sync bypass, replay-without-mutation.
- **Event bus & usage** — `event-handler-dependency-graph`: Kahn levels with cached execution plans and aemit bypass.
- **Event bus & usage** — `usage-aggregation-ownership`: reentrant-safe listener attach/detach around kickoff ownership.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question against project `ext-crewAI`. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Re-run probes byte-exact from the repo root (`/mnt/hdd/utopia/inspo/external/crewAI`, runner `.venv/bin/python -m pytest`) before shipping.

## Provenance
crewAI (MIT), `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory project `ext-crewAI` (353,322 nodes / 463,414 edges, status ready, head==base==pin 9e9a8577 after ff-pull of f4731f50→9e9a8577 and in-place refresh; content freshness proven by resolving drift-introduced `project_created_span` via search_code line-exact at lib/crewai-core/src/crewai_core/telemetry.py:411; parse_partial ×142 = versioned docs .mdx + CLI templates + viz assets, none cited).

## Full view (memory graph)
Revalidate `ext-crewAI` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph root `/mnt/hdd/utopia/inspo/external/crewAI`, branch main, pin 9e9a8577, FULL mode, generation_matches verified; coverage check stdin-JSON over 14 cited kernel paths returned no_recorded_issue + metadata_match ×14. BM25 search_graph is healthy on this corpus (unlike doc-shaped repos) but search_code resolves file-stem anchors line-exact when queries miss. Source and direct tests decide shipped claims.

## Boundaries
Adopt pure engine contracts (listener ledgers, pairing invariants, append-only snapshots, backend-setter pattern); adapt transport details (Redis/file locks, SQLite, CEL) to your host stack; omit product surfaces not mined here (Crew/Agent internals, tools catalog, enterprise Plus API, telemetry exporters, visualization assets).

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`RECONCILIATION-NOTES.md`](./RECONCILIATION-NOTES.md)
- [`and-condition-pending-ledger.md`](./and-condition-pending-ledger.md)
- [`ask-timeout-executor-discipline.md`](./ask-timeout-executor-discipline.md)
- [`auto-checkpoint-event-fanout.md`](./auto-checkpoint-event-fanout.md)
- [`cel-template-interpolation.md`](./cel-template-interpolation.md)
- [`checkpoint-config-coercion.md`](./checkpoint-config-coercion.md)
- [`checkpoint-filename-lineage.md`](./checkpoint-filename-lineage.md)
- [`checkpoint-version-migration.md`](./checkpoint-version-migration.md)
- [`conditional-start-entry-ladder.md`](./conditional-start-entry-ladder.md)
- [`context-recovery-ladder.md`](./context-recovery-ladder.md)
- [`crew-kickoff-scheduling.md`](./crew-kickoff-scheduling.md)
- [`crew-task-pipeline.md`](./crew-task-pipeline.md)
- [`declarative-action-builder.md`](./declarative-action-builder.md)
- [`declarative-method-field-recovery.md`](./declarative-method-field-recovery.md)
- [`deterministic-fingerprints.md`](./deterministic-fingerprints.md)
- [`distributed-named-lock-backend.md`](./distributed-named-lock-backend.md)
- [`event-bus-dispatch.md`](./event-bus-dispatch.md)
- [`event-bus-dual-plane-dispatch.md`](./event-bus-dual-plane-dispatch.md)
- [`event-handler-dependency-graph.md`](./event-handler-dependency-graph.md)
- [`event-scope-pairing.md`](./event-scope-pairing.md)
- [`executor-flow-state.md`](./executor-flow-state.md)
- [`feedback-outcome-collapse-ladder.md`](./feedback-outcome-collapse-ladder.md)
- [`finalize-synthesis.md`](./finalize-synthesis.md)
- [`flow-ask-blocking-input.md`](./flow-ask-blocking-input.md)
- [`flow-engine-loop-safety.md`](./flow-engine-loop-safety.md)
- [`flow-hooks-ladder.md`](./flow-hooks-ladder.md)
- [`flow-kickoff-dual-mode-entry.md`](./flow-kickoff-dual-mode-entry.md)
- [`flow-runtime-dag-engine.md`](./flow-runtime-dag-engine.md)
- [`flowmeta-field-triage.md`](./flowmeta-field-triage.md)
- [`fork-vs-resume-state-identity.md`](./fork-vs-resume-state-identity.md)
- [`handler-dependency-levels.md`](./handler-dependency-levels.md)
- [`hitl-pause-resume-protocol.md`](./hitl-pause-resume-protocol.md)
- [`hook-pairing-exactly-once.md`](./hook-pairing-exactly-once.md)
- [`human-feedback-outcome-split.md`](./human-feedback-outcome-split.md)
- [`human-feedback-pause-resume.md`](./human-feedback-pause-resume.md)
- [`human-feedback-rerun.md`](./human-feedback-rerun.md)
- [`listener-cycle-reentry.md`](./listener-cycle-reentry.md)
- [`llm-stop-param-recovery.md`](./llm-stop-param-recovery.md)
- [`memory-drain-before-finished.md`](./memory-drain-before-finished.md)
- [`multimodal-file-injection.md`](./multimodal-file-injection.md)
- [`native-tool-batch.md`](./native-tool-batch.md)
- [`or-listener-fire-once-rearm-racing.md`](./or-listener-fire-once-rearm-racing.md)
- [`or-listener-fired-ledger.md`](./or-listener-fired-ledger.md)
- [`persist-backend-precedence.md`](./persist-backend-precedence.md)
- [`persistence-factory-pluggable-default.md`](./persistence-factory-pluggable-default.md)
- [`plan-execute-flow-graph.md`](./plan-execute-flow-graph.md)
- [`planner-observation-parsing.md`](./planner-observation-parsing.md)
- [`planning-llm-contract.md`](./planning-llm-contract.md)
- [`prompt-cache-breakpoints.md`](./prompt-cache-breakpoints.md)
- [`provider-tool-call-normalization.md`](./provider-tool-call-normalization.md)
- [`racing-or-listeners-first-wins.md`](./racing-or-listeners-first-wins.md)
- [`react-parser.md`](./react-parser.md)
- [`reasoning-effort-ladder.md`](./reasoning-effort-ladder.md)
- [`replan-machinery.md`](./replan-machinery.md)
- [`replay-vs-emit-duality.md`](./replay-vs-emit-duality.md)
- [`router-dispatch-loop.md`](./router-dispatch-loop.md)
- [`rpm-and-force-finish.md`](./rpm-and-force-finish.md)
- [`sqlite-flow-persistence.md`](./sqlite-flow-persistence.md)
- [`sqlite-flow-state-ledger.md`](./sqlite-flow-state-ledger.md)
- [`state-copy-discipline.md`](./state-copy-discipline.md)
- [`state-id-guarantee-ladder.md`](./state-id-guarantee-ladder.md)
- [`step-executor-worker.md`](./step-executor-worker.md)
- [`stream-frame-pipeline.md`](./stream-frame-pipeline.md)
- [`sync-method-thread-isolation.md`](./sync-method-thread-isolation.md)
- [`task-agent-handoff.md`](./task-agent-handoff.md)
- [`todo-dependency-scheduler.md`](./todo-dependency-scheduler.md)
- [`tool-cache-and-limits.md`](./tool-cache-and-limits.md)
- [`tool-cache-opt-in.md`](./tool-cache-opt-in.md)
- [`tool-failure-protocol.md`](./tool-failure-protocol.md)
- [`tool-failure-taxonomy.md`](./tool-failure-taxonomy.md)
- [`usage-aggregation-ownership.md`](./usage-aggregation-ownership.md)
- [`usage-aggregation-reentrancy.md`](./usage-aggregation-reentrancy.md)
- [`wrapped-method-descriptor-binding.md`](./wrapped-method-descriptor-binding.md)
- [`writer-priority-rw-lock.md`](./writer-priority-rw-lock.md)
- [`xrepo-appendonly-snapshot-ledger.md`](./xrepo-appendonly-snapshot-ledger.md)
- [`xrepo-copycontext-thread-hop.md`](./xrepo-copycontext-thread-hop.md)
- [`xrepo-event-scope-pairing.md`](./xrepo-event-scope-pairing.md)
- [`xrepo-first-wins-racing.md`](./xrepo-first-wins-racing.md)
- [`xrepo-pause-as-return-hitl.md`](./xrepo-pause-as-return-hitl.md)
- [`xrepo-processwide-backend-setter.md`](./xrepo-processwide-backend-setter.md)
