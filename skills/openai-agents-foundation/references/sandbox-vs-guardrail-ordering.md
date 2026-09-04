<!-- capsule-v2 -->
# Sandbox-vs-guardrail ordering — why do sequential input guardrails run before sandbox preparation?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** In a run that enables both blocking input guardrails and a sandbox runtime, which fires first and what state is allowed to exist before a tripwire aborts?

## Pre-sandbox sequential gate
**Path/Symbol:** `src/agents/run_internal/run_loop.py:` :1159–1190 (streamed loop, mirrored by the sync runner), with `persist_session_items_for_guardrail_trip` from `session_persistence.py`.
**Signature:** part of `start_streaming(...)`'s per-iteration preamble; `sandbox_runtime.prepare_agent(current_agent=..., current_input=..., context_wrapper=..., is_resumed_state=...)`.
**Data Shape:** guardrails partitioned once per loop iteration into `sequential_guardrails` (`run_in_parallel=False`) vs `parallel_guardrails`; trip detection compares `input_guardrail_results[existing_count:]`.

### Decisive source
```python
if sandbox_runtime is not None and sandbox_runtime.enabled and sequential_guardrails:
    # Mirror the non-streaming path: a blocking first-turn guardrail should fire
    # before sandbox prep can create, start, or mutate sandbox state.
    existing_input_guardrail_count = len(streamed_result.input_guardrail_results)
    await run_input_guardrails_with_queue(starting_agent, sequential_guardrails, ...)
    for result in streamed_result.input_guardrail_results[existing_input_guardrail_count:]:
        if result.output.tripwire_triggered:
            streamed_result._event_queue.put_nowait(QueueCompleteSentinel())
            session_input_items_for_persistence = (
                await persist_session_items_for_guardrail_trip(...)
            )
            raise InputGuardrailTripwireTriggered(result)
    sequential_guardrails = []
```
After the gate passes (or without sequential guardrails): `prepare_agent` may REWRITE input — the rewrite is reconciled through `reconcile_nested_history_owned_input_after_rewrite` so ownership refs survive, then mirrored onto `streamed_result.input/_original_input` AND `run_state`.

**Flow:** sequential guardrails (only those that opted out of parallelism) run against the PREPARED turn input BEFORE sandbox prep → any trip persists the caller input for recovery → sentinel enqueued → exception raised. Only surviving input reaches `prepare_agent`. Parallel guardrails launch as a background task later (turn 1) and surface via the pre-side-effects check.

**Invariant:** No sandbox VM creation/start/mutation may happen before a blocking guardrail has had its verdict — otherwise every tripwire leaks a started machine. Input rewrites by the sandbox must flow through the nested-history reconciliation or owned-item refs dangle.

**Probe:** deterministic source-pin (both runners carry the identical comment contract); guardrail-timing probes: `tests/test_stream_input_guardrail_timing.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "sandbox prepare agent sequential guardrails tripwire", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt "cheap verdicts before expensive resource creation" ordering for any guarded side-effectful setup; adapt the partition criterion; omit session-trip persistence if your runs are stateless.
