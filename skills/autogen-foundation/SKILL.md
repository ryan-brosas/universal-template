---
name: autogen-foundation
description: "Use when porting multi-agent orchestration machinery from Microsoft AutoGen (Python): single-queue envelope runtime, topic/subscription message bus, intervention hooks at dequeue time, group-chat supervisor loops (round-robin, LLM selector, swarm handoff, DAG graph flow), FIFO ordered delivery, termination algebra, run/stream lifecycle, bounded agent tool-call loops, RPC cancellation/failure ladders, name-keyed team checkpointing, middle-out token-budget contexts, mutate-and-report memory injection, subprocess executor timeout/cancel exit codes, grpc worker/host registration handshake with request-id correlation and disconnect cleanup, streamed tool-call workbenches, and pluggable model-context recall strategies."
---

# AutoGen: Agent Runtime & Group-Chat Foundations

## Use this for
Use when building or porting a multi-agent orchestration layer in Python: a minimal agent runtime that drives RPC sends and topic publishes through one asyncio queue of typed envelopes, type-keyed lazy agent factories, topic subscriptions where the topic source becomes the agent instance key, dispatch-time intervention handlers, and the agentchat supervisor stack — a manager that selects speakers from participant descriptions or explicit handoff messages or a validated dependency graph, containers that buffer broadcast history for their delegates, an event-handoff FIFO lock that makes concurrent delivery order contractual, composable stateful termination conditions with reset semantics, and a stream API whose terminal marker is guaranteed even when the runtime dies mid-run. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump

### Core runtime plane (`autogen-core`)
- `references/runtime-envelope-dispatch.md` — one queue, three envelope types; delivery paths pay task_done per envelope, intervention early-return arms leak it.
- `references/intervention-pipeline.md` — on_send/on_publish/on_response interception; None-warn, DropMessage-sentinel, asymmetric failure handling.
- `references/publish-sender-skip-gather.md` — full-identity sender skip; gather barrier; fail-loud vs fail-latch constructor flag.
- `references/lazy-agent-instantiation.md` — factory-per-type vs instance-per-id; construction-time context injection.
- `references/handler-routing-ladder.md` — decorator-stamped target types + router predicates; exact-type first-match dispatch.
- `references/type-subscription-prefix.md` — source-becomes-key tenancy; colon-prefixed direct-message topics.
- `references/subscription-registry.md` — rebuild-on-mutation recipient cache; pair-equality duplicate rejection; one unguarded manager shared by three runtimes.
- `references/run-lifecycle-shutdown.md` — stop vs stop_when_idle vs legacy stop_when; vendored queue shutdown; fresh-queue reset.
- `references/dequeue-intervention-ordering.md` — enqueue-clean/dequeue-intercepted ordering; Drop precedes recipient resolution; early-return arms skip task_done.
- `references/serialization-registry-type-dispatch.md` — (type_name, content-type)-keyed serializer registry; deserialize returns UnknownPayload values, serialize raises; bare-name collision hazard.

### Distributed runtime plane (`autogen-ext` grpc worker/host)
- `references/grpc-registration-handshake.md` — local-factory-first then host RegisterAgent unary RPC; exclusive type→client claims with INVALID_ARGUMENT abort.
- `references/grpc-request-correlation.md` — lock-guarded monotonic request_ids parking futures before enqueue; errors cross the wire as strings.
- `references/grpc-host-disconnect-recovery.md` — OpenChannel finally-cleanup ladder cancels pending futures and revokes types/subscriptions; worker-side reconnect does not exist.

### Group-chat supervisor plane (`autogen-agentchat`)
- `references/team-topic-topology.md` — UUID-scoped topic types wiring participants, manager, and output tap.
- `references/supervisor-turn-loop.md` — start-RPC → responses-as-events → `_active_speakers` barrier → select next.
- `references/fifo-sequential-lock.md` — event-handoff lock making processing order == arrival order under concurrent delivery.
- `references/container-buffer-drain.md` — buffer-on-broadcast, drain-on-request; clear-only-on-success; double-reported delegate errors.
- `references/termination-algebra.md` — delta-consuming conditions, AND/OR composition, reuse raises outside normal handling.
- `references/selector-retry-ladder.md` — violation-specific feedback retries then deterministic fallback; three-variant mention regex.
- `references/selector-context-transcript.md` — pluggable ChatCompletionContext flattened into one prompt message; previous-speaker gating; per-turn retry scratchpad.
- `references/swarm-handoff-state.md` — last-handoff-wins reversed scan; latest-target validation only.
- `references/graph-activation-groups.md` — (target, activation_group) join countdowns, fire-time re-arm, cycle-without-exit rejection.
- `references/run-stream-output-plumbing.md` — single output relay, guaranteed GroupChatTermination marker, queue drain in finally.
- `references/team-pause-resume-rpc.md` — out-of-band empty-marker RPCs to participants+manager; cooperative no-op agent defaults; run loop untouched.

### Agent, context & memory planes
- `references/assistant-tool-call-loop.md` — range-bounded model↔tool loop; gather barrier; None-sentinel stream; errors become results.
- `references/rpc-cancellation-ladder.md` — sync-lock token linked after enqueue; cancelled()-guarded set_result/set_exception; dispatch-time recipient failure.
- `references/team-state-checkpointing.md` — participant-name-keyed save/load through thin runtime delegation; refuse-while-running mutex.
- `references/model-usage-protocol.md` — RequestUsage dataclass rides every completion; clients expose count_tokens/remaining_tokens only.
- `references/token-budget-middle-out.md` — pop-the-middle eviction driven by client accounting; orphaned leading function-result repaired.
- `references/local-code-executor-limits.md` — wait_for ladder with exit codes 124 (timeout) / 125 (cancelled); terminate+await cleanup; fail-fast blocks.
- `references/memory-update-context.md` — stores mutate the context AND return what they added; retrieval strategy stays inside the store.
- `references/workbench-stream-holdback.md` — hold-back-one stream protocol; terminal ToolResult guaranteed last; error-as-result; ExceptionGroup flattening.
- `references/buffered-context-view-trim.md` — storage stays complete, only get_messages trims; checkpoints serialize the full list.
- `references/tool-schema-run-json-gate.md` — declaration-time schema generation; strict violations surface at `.schema` access; model_validate gates execution.
- `references/model-client-stream-contract.md` — chunks are cosmetic, one terminal CreateResult is authoritative; missing terminal fails loud.

## Capsule map

**Core runtime plane**
- **Envelope dispatch** — `runtime-envelope-dispatch`: SendMessage/Publish/Response envelopes share one asyncio.Queue; each dequeue spawns a background delivery task; futures resolve only via later Response turns; delivery paths pay task_done but intervention early-return arms leak it (join() can hang).
- **Interventions** — `intervention-pipeline`: mutate-in-place interception at send/publish/response; returning None warns, DropMessage drops, handler exceptions reach the awaiting caller on RPC paths but are logged-and-swallowed on publish.
- **Fan-out** — `publish-sender-skip-gather`: sender skipped by full `(type, key)` identity; subscriber coroutines gathered; unhandled failures latched into `_background_exception` only when `ignore_unhandled_exceptions=False`.
- **Instantiation** — `lazy-agent-instantiation`: one factory per type string (dup raises), one cached instance per AgentId, factories invoked under a contextvar context so agents self-discover runtime/id.
- **Routing** — `handler-routing-ladder`: `@event`/`@rpc` stamp target_types/produces_types/router; dispatch is concrete-type bucket lookup, first matching router wins, no inheritance.
- **Subscriptions** — `type-subscription-prefix`: TypeSubscription maps `topic.source` → agent key (per-source instances); direct messages ride `"<agent_type>:"` prefix subscriptions — the colon is load-bearing.
- **Subscription registry** — `subscription-registry`: seen-topic set + full cache rebuild on every add/remove; duplicates rejected by id-or-(agent_type,topic_type) equality; zero internal locks — shared by core publish, grpc worker, and host servicer on one loop.
- **Serialization** — `serialization-registry-type-dispatch`: serializers keyed by (type_name, content-type); deserialize-miss returns an UnknownPayload value while serialize-miss raises; protobufs use descriptor full names, other classes bare names.
- **Lifecycle** — `run-lifecycle-shutdown`: `stop()` discards pending work, `stop_when_idle()` joins the queue first; every flavor resets to a fresh Queue so runtimes are re-runnable.
- **Interception order** — `dequeue-intervention-ordering`: publish_message enqueues with no hook; _process_next intercepts after get(); publish-arm failures are logged-and-returned (publisher never learns); early returns skip task_done so join-based shutdown can hang.

**Supervisor plane**
- **Topology** — `team-topic-topology`: every team namespacing is suffixed with an instance UUID; participants get self+broadcast subs, the manager gets self+broadcast+output-tap subs.
- **Turn loop** — `supervisor-turn-loop`: speaker selection returns one-or-many names; outstanding-speaker list gates advancement; termination resets condition+turn counter BEFORE signaling so teams rerun.
- **Ordering** — `fifo-sequential-lock`: per-agent FIFO grant order for declared sequential message types via Event-queue handoff (never plain asyncio.Lock).
- **Delegation** — `container-buffer-drain`: delegates receive the buffered transcript at request time; buffer cleared only after a successful turn; exceptions broadcast as GroupChatError AND re-raise.
- **Termination** — `termination-algebra`: conditions consume deltas and latch; AND joins stop messages across deltas and raises TerminatedException(BaseException) on reuse; OR raises RuntimeError.
- **LLM selection** — `selector-retry-ladder`: zero/multi/repeated mentions each get tailored feedback and a retry; after max attempts fall back previous-speaker → first-participant; mention regex matches name, spaces-for-underscores, escaped underscores with \W boundaries and padding.
- **Handoffs** — `swarm-handoff-state`: reversed thread scan for newest HandoffMessage decides the sole next speaker; only the LATEST handoff's target is validated.
- **Graph execution** — `graph-activation-groups`: conditional edges decrement (target,group) counters ("all") or enqueue-once ("any"); triggered groups re-arm at dequeue; cycles need a conditional exit edge plus termination/max_turns.
- **Streaming** — `run-stream-output-plumbing`: manager relays the output topic into a plain asyncio.Queue; a backstop shutdown task synthesizes GroupChatTermination(with error) if the runtime dies; consumer drains the queue in finally.
- **Pause/resume** — `team-pause-resume-rpc`: pause()/resume() fan empty GroupChatPause/Resume marker RPCs to every participant plus the manager; containers recurse into nested teams; agents cooperate via overridable no-op on_pause/on_resume; run/run_stream never return.
- **Selector context** — `selector-context-transcript`: the whole (pluggable, default-unbounded) model context is flattened to "source: content" lines inside ONE prompt message; SystemMessage for OpenAI family else UserMessage; _previous_speaker filters candidates but mention checks see all names; selector state persists thread+turn+previous_speaker.

**Agent, context & memory plane**
- **Tool loop** — `assistant-tool-call-loop`: exactly max_tool_iterations LLM calls when every turn is function calls; concurrent execution observed via stream events, context mutated only after ALL results; bad JSON args / unknown tool names yield FunctionExecutionResult(is_error=True).
- **Cancellation** — `rpc-cancellation-ladder`: cancel() is synchronous/idempotent under threading.Lock; link_future AFTER enqueue; both resolution arms guard `not future.cancelled()`; unknown recipient raises at the caller before queuing.
- **Checkpointing** — `team-state-checkpointing`: {"agent_states": {name: state}} keyed by NAME not AgentId; TeamState validation; _is_running mutex cleared in finally; lazy factory instantiation on load.
- **Usage protocol** — `model-usage-protocol`: plain dataclass usage(prompt, completion) on every CreateResult; remaining_tokens may go negative BY DESIGN (that sign drives eviction).
- **Budget eviction** — `token-budget-middle-out`: pops len//2 until under budget (recent AND oldest survive), then strips an orphaned leading FunctionExecutionResultMessage.
- **Executor limits** — `local-code-executor-limits`: subprocess linked to the token; TimeoutError⇒124, CancelledError⇒125, always terminate()+wait(); nonzero exit skips later blocks.
- **Memory** — `memory-update-context`: update_context mutates the ChatCompletionContext and returns the added memories; List injects one numbered SystemMessage, vector stores derive the query from the last message.
- **Streamed tools** — `workbench-stream-holdback`: yield previous only when the next arrives so exactly one ToolResult terminates every stream; mid-stream errors flush held chunk then error-result; unknown tools never raise.
- **Recall contexts** — `buffered-context-view-trim`: tail-n is a per-read view; orphaned leading FunctionExecutionResultMessage dropped from the view; save_state serializes the FULL list.
- **Tool schemas** — `tool-schema-run-json-gate`: BaseTool generates JSON schemas at declaration (jsonref $defs inlining); strict mode raises at .schema access when defaults exist or additionalProperties is set; run_json model_validates args before run().
- **Stream contract** — `model-client-stream-contract`: create_stream yields str display chunks then exactly one authoritative CreateResult; AssistantAgent captures the terminal and fails loud if a stream ends without it.

**Distributed runtime plane (grpc)**
- **Registration** — `grpc-registration-handshake`: factory stored locally then unary RegisterAgent; host's locked type→client map rejects duplicates across workers with INVALID_ARGUMENT; subscriptions commit host-first, mirror locally second.
- **Wire correlation** — `grpc-request-correlation`: monotonic request_ids under an asyncio.Lock park futures before enqueue; replies pop-and-resolve; agent exceptions cross as str(e) and re-raise as generic Exception.
- **Disconnect** — `grpc-host-disconnect-recovery`: OpenChannel finally deletes the connection, cancels its pending response futures, revokes its types/subscriptions; worker detects nothing (EOF breaks a silent read task) — no reconnect exists, only UNAVAILABLE retryPolicy on unary calls.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
autogen (MIT — LICENSE-CODE), `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (full mode, canonical root /mnt/hdd/utopia/inspo/autogen, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z, generation_matches true; parse_partial ×9 confined to dotnet tooling/docs templates and cookiecutter pyproject — none cited). The earlier twin project `ext-autogen` is retired; revalidate against `autogen`.

## Full view (memory graph)
Revalidate `autogen` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the framework-neutral contracts: envelope+queue dispatch with strict completion accounting (caveat: intervention early-returns skip task_done), source-keyed tenancy, dequeue-time intervention taxonomy, FIFO event-handoff ordering, buffer/drain delegation, join-countdown graph execution, delta-consuming termination algebra, guaranteed stream termination, error-as-result bounded tool loops and streamed workbench results, cancelled-guarded future resolution, name-keyed checkpoints, middle-out budget eviction, mutate-and-report memory injection, view-only model-context trimming, exclusive type-claim registration with request-id wire correlation, and connection-scoped disconnect cleanup. Adapt topic naming, serialization registries, tokenizer-backed token counting, and the pydantic Component save/load layer to your host. Omit the .NET/in-progress AutoGen runtime half of the repo, autogen-studio product surface (FastAPI/React), the remaining autogen-ext model clients, MagenticOne orchestration prompts, OpenTelemetry attribute plumbing, the grpc control channel (`OpenControlChannel`/destination-prefix routing), and worker-side reconnect (upstream never implemented it) unless you target the same stack.
