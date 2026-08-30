---
name: mastra-foundation
description: "Use when building a TypeScript agent framework or workflow engine — snapshot-persisted suspend/resume workflow DAGs, state-reader nested path navigation, agent-loop snapshot pruning, run-scope serialization boundary, resumable stream replay caching, agent tool memory isolation, Graph RAG serialization, LLM relevance scoring, ACP tool adapters, and the control-flow execution kernel (parallel/conditional/loop/foreach handlers with durable-engine hooks)."
disable-model-invocation: true
---

# mastra: TypeScript Agent Framework Foundation

## Use this for
Use when building a TypeScript agent framework or workflow engine: DAG-based step execution with snapshot-backed suspend/resume, nested path state navigation, snapshot-size pruning without breaking resume, non-serializable runtime state kept off the JSON wire, disconnect/reconnect stream replay, request-context memory isolation across sub-agents, external signal providers, Graph RAG JSON snapshot serialization, prompt-engineered LLM relevance rerankers, ACP protocol tool bridges, cycle-free observational memory integration, or porting the control-flow execution kernel itself — parallel failure-status reduction, condition-arm selection, loop cancellation placement, foreach fluid concurrency with per-iteration progress persistence, and the durable-engine hook lattice. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/workflow-suspend-resume-state-machine.md` — workflow snapshot loading, suspend status validation, label resolution, and unambiguous multi-step auto-detection.
- `references/workflow-state-reader-nested-paths.md` — state-reader read model, array step inspection, and hierarchical nested suspend path unwrapping.
- `references/workflow-step-execution-dag.md` — DAG topological execution, run context binding, parallel branch evaluation, and terminal result shaping.
- `references/agent-tool-memory-isolation.md` — request-context `MastraMemory` snapshot and unconditional restoration across nested sub-agent tool invocations.
- `references/agent-loop-tool-call-suspension.md` — agentic loop tool call suspension, permission request packaging, and deterministic resume labels.
- `references/graph-rag-snapshot-serialization.md` — JSON-safe Graph RAG snapshot schema with load-time node validation and direct reciprocal edge assignment.
- `references/agent-relevance-scorer.md` — prompt-engineered LLM text relevance scorer with strict bounded float parsing `[0.0, 1.0]`.
- `references/acp-tool-adapter-protocol.md` — Agent Client Protocol (ACP) tool bridge with typed `permissionRequest` suspend schema and `selected`/`cancelled` resume schema union.
- `references/claude-sdk-stream-synthesis.md` — 3-phase completed stream synthesis (Start $\to$ TextDelta $\to$ Finish with usage and cost context).
- `references/observational-memory-workflow-kernel.md` — cycle-free observational memory snapshot projections and processor workflow integration.
- `references/agent-loop-snapshot-pruning.md` — status-matrix snapshot pruning: terminal vs non-terminal strip rules, request-echo removal, `__workflowKind` restore, foreach per-entry recursion.
- `references/workflow-run-output-lifecycle.md` — promise-facing stream output with three settlement paths (close/pipe-reject/explicit-reject) and per-subscriber detachable fanout.
- `references/stream-replay-caching.md` — cache-on-transform + history-first replay reader for disconnect/reconnect without PubSub.
- `references/run-scope-wire-boundary.md` — typed per-run scope for non-JSON-safe handles; hydrate-bootstrap-only, read-fallback/write-mirror legacy contract, refcounted lifecycle.
- `references/signal-provider-subscription-plane.md` — triple-index subscription registry, overlap-guarded unref'd polling, webhook routing, error-contained poll cycles.
- `references/smooth-stream-chunking.md` — detector-driven text pacing with part-id buffer generations and metadata-only-tail preservation.
- `references/server-cache-list-contract.md` — seven-method cache surface (list/LRANGE/increment) behind resumable streaming; TTL-normalizing in-memory reference.
- `references/loop-entry-normalization.md` — `_internal` bag rebuild-or-silently-drop rule, injectable id/clock, first-suspended-step stream-state resurrection.
- `references/parallel-failure-status-lattice.md` — which branch's result wins when parallel branches end mixed (failed > suspended > canceled > success), with explicit tripwire propagation.
- `references/conditional-arm-selection.md` — throw-to-false condition semantics plus skipped-reconciliation of unselected time-travel arms.
- `references/loop-cancellation-triple.md` — where a do-while/until loop must check abort, and how iteration counts resume from metadata.
- `references/foreach-fluid-concurrency-queue.md` — fastq-based fluid concurrency with kill-drain in-flight accounting and order-true index-keyed results.
- `references/foreach-failure-progress-persistence.md` — why failed foreach runs must carry `__workflow_meta.foreachOutput` (upstream #21749 duplicate-side-effects regression).
- `references/foreach-resume-index-routing.md` — routing the resume payload to the exact suspended iteration (explicit forEachIndex vs derived regimes).
- `references/engine-durability-hooks.md` — the DefaultExecutionEngine override lattice (wrapDurableOperation, evaluateCondition index-or-null, span hooks) that adapts one engine to replay-based hosts.
- `references/sleep-duration-normalization.md` — duration clamps, nodate early-return, dynamic date rehydration, and re-throw-after-error-span semantics.
- `references/block-resume-reassembly.md` — rebuilding a block-level result after resuming one branch: all-membership vs only-executed rules, mutable resumePath shift-consumption.
- `references/foreach-concurrency-resolver.md` — static-or-function concurrency resolution with floor-at-1 degradation (never throws).
- `references/reentry-result-field-hygiene.md` — the exact eight-field strip every step-result reuse must apply before a new attempt.
- `references/event-emission-gate.md` — the strict `emitStepEvents === false` wrapper pattern and watch-event topic grammar.

## Capsule map
- **Workflow Engine & State Machine** — `workflow-suspend-resume-state-machine`, `workflow-state-reader-nested-paths`, `workflow-step-execution-dag`: snapshot persistence, multi-branch suspend detection, nested path unwrapping, DAG run boundaries.
- **Snapshot Persistence & Pruning** — `agent-loop-snapshot-pruning`: per-status strip matrix keeping resume state while dropping dead weight (24%-of-bytes request echo).
- **Runtime State & Wire Boundary** — `run-scope-wire-boundary`, `loop-entry-normalization`: typed scope slots off the stringify wire, hydrate-once/fallback-read/mirror-write contract, entrypoint field-forwarding invariants.
- **Stream Plane** — `workflow-run-output-lifecycle`, `stream-replay-caching`, `smooth-stream-chunking`, `server-cache-list-contract`: settlement-path-complete output object, gap-free history+live replay, metadata-preserving chunk pacing, minimal cache backend contract.
- **Agent Runtime & Memory Isolation** — `agent-tool-memory-isolation`, `agent-loop-tool-call-suspension`, `observational-memory-workflow-kernel`: request-context thread restoration, tool permission suspension, cycle-free observational memory snapshots.
- **External Events** — `signal-provider-subscription-plane`: provider-to-thread notification bridge with idempotent subscriptions and safe polling.
- **Graph RAG & Reranking** — `graph-rag-snapshot-serialization`, `agent-relevance-scorer`: JSON snapshot deep-cloning with reciprocal edge assignment, bounded float relevance parsing.
- **Protocol & SDK Bridges** — `acp-tool-adapter-protocol`, `claude-sdk-stream-synthesis`: typed ACP tool permissions, 3-phase stream chunk synthesis.
- **Control-flow execution kernel** — `parallel-failure-status-lattice`, `conditional-arm-selection`, `loop-cancellation-triple`: one status per block under fixed precedence; conditions fail soft; loops bracket both awaits with abort checks.
- **Foreach engine** — `foreach-fluid-concurrency-queue`, `foreach-failure-progress-persistence`, `foreach-resume-index-routing`, `foreach-concurrency-resolver`: fluid fastq concurrency, progress persisted on suspend AND failure paths, per-index resume routing, floor-at-1 validation.
- **Durability seam** — `engine-durability-hooks`: the full DefaultExecutionEngine override surface (Inngest subclass is the reference consumer) plus mutable-context round-trip.
- **Time, events & state hygiene** — `sleep-duration-normalization`, `event-emission-gate`, `block-resume-reassembly`, `reentry-result-field-hygiene`: clamped waits via engine hooks; strict-equality event gate; block rebuild after single-branch resume; eight-field terminal-state strip at every re-entry.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Natural next seams: `handlers/step.ts` retry ladder + nested-workflow dispatch, `evented/workflow-event-processor/index.ts` (3,123L queue-driven twin of the control-flow plane), `dynamic/serialize.ts|rehydrate.ts` snapshot schema round-trip.

## Provenance
mastra (Apache-2.0 / ELv2 portions under ee/, not mined), `main@502653550fb45d8e72dfdd57732161f9176dbcf2`; Codebase Memory project `ext-mastra` (root `/mnt/hdd/utopia/inspo/external/mastra`, FULL mode, 159,026n/638,590e, head==base==origin/main at pass 3, 2026-08-24; parse_partial ×40 = CSS/test fixtures/pnpm-lock lines, none cited). Pass 1 (10 capsules): workflows/agent/rag/acp/claude-sdk/observational-memory planes @ `3d2ff0d0`. Pass 2 (+7→17 recorded, 18 on disk): loop/stream/run-scope/signals/cache planes, same pin. Pass 3 (+12 → 30): drift re-entry (+23 upstream commits ff-pulled, re-indexed IN PLACE through unchanged registered root — no twin), control-flow handler kernel mined whole-file (control-flow.ts 1,443L, sleep.ts, entry.ts block-resume, utils.ts resolvers, default.ts hook lattice).

## Full view (memory graph)
Revalidate `ext-mastra` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. BM25 `search_graph` resolves Function-class nodes line-exact on this corpus (verified at pass 3: executeParallel :101-273, resolveForeachConcurrency :786-796); use `search_code --pattern` for prose/doc targets.

## Boundaries
Adopt the workflow suspend/resume state machine, the snapshot-pruning strip matrix, the run-scope wire boundary, request-context memory isolation, Graph RAG snapshot schemas, ACP tool adapter contracts, and the control-flow status/cancellation/persistence contracts. Adapt storage driver interfaces, token budget thresholds, signal key grammar, telemetry envelopes, pubsub topics, and snapshot key names per host. Omit product UI components (`playground/`, `playground-ui/`, `factory-ui/`) and cloud task services unless specifically required.
