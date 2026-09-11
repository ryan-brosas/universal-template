<!-- capsule-v2 -->
# Turn-span × persistence boundary — which failures reach the turn-span finally with partial usage, and what persists after the span closes?

**Source:** OpenAI Agents Python MIT `main@fe45b415ee05`; Codebase Memory project `openai-agents-python` (MCP absent this pass — direct source+test reading fallback per AGENTS.md). **Question:** Where exactly does the turn span sit relative to per-turn state sync, guardrail trips, model errors, and session persistence — i.e., when does a turn export partial usage, and what is saved inside vs after the span?

## Span window vs persistence window
**Path/Symbol:** non-streamed `src/agents/run.py:` turn-span create :1615–1630 (`turn_usage_start = snapshot_usage` → `turn_span(...)` → `start(mark_as_current=True)`), finally :1753–1760 (`attach_usage_to_span(usage_delta(...))` + `finish(reset_current=True)`), post-finally persistence :1800–1860; streamed twin `src/agents/run_internal/run_loop.py:` create :1736–1746, `run_single_turn_streamed` await :1758, finally :1779–1784, post-finally `raw_responses`/tracker snapshot :1786–1800; streamed in-span persistence `run_loop.py` `_should_persist_stream_items` (:322+) / `_save_stream_items` (:409+).
**Signature:** `turn_usage_start = snapshot_usage(context_wrapper.usage)`; `finally: attach_usage_to_span(current_turn_span, usage_delta(turn_usage_start, context_wrapper.usage)); current_turn_span.finish(reset_current=True)`.
**Data Shape:** `use_task_and_turn_spans` from `RunConfig.tracing`; usage delta computed from context-wrapper usage snapshots, not from the model response.

### Decisive source
```python
turn_usage_start = snapshot_usage(context_wrapper.usage)
current_turn_span = turn_span(turn=current_turn, agent_name=current_agent.name) \
    if use_task_and_turn_spans else None
if current_turn_span is not None:
    current_turn_span.start(mark_as_current=True)
try:
    ...  # input guardrails (turn 1), model_task / run_single_turn(_streamed)
finally:
    if current_turn_span is not None:
        attach_usage_to_span(
            current_turn_span,
            usage_delta(turn_usage_start, context_wrapper.usage),
        )
        current_turn_span.finish(reset_current=True)
```
and the non-streamed post-finally gate:
```python
items_to_save_turn = list(turn_session_items)
if not isinstance(turn_result.next_step, NextStepInterruption):
    if session_persistence_enabled:
        ...  # save_result_to_session AFTER the span is already finished
```

**Flow:** per-turn state synchronization (`_synchronize_accepted_run_state`, blocked-output owner starts, `items_for_model` selection) happens BEFORE span creation; between creation and the `try` body only `start()` runs, so nothing can abort "before the span". Every turn-body failure — input-guardrail tripwire (turn 1, including the parallel-gather cancel-and-drain branch), model error, tool failure, max-turns — unwinds through the finally and exports a PARTIAL usage delta: usage is never lost, it is simply whatever accumulated up to the failure. Nothing about the span depends on the turn succeeding. Non-streamed: session persistence for the turn runs AFTER the finally, skipped entirely for `NextStepInterruption` (approval pending ⇒ nothing saved). Streamed: item saves happen INSIDE `run_single_turn_streamed` (inside the span) via the persistence gate, while `raw_responses` extension and the tool-use-tracker snapshot happen after the finally.

**Invariant:** (1) The turn span always finishes exactly once per turn, on success or any failure, with the usage delta up to that point — partial usage is correct output, not a bug. (2) No raising code sits between span creation and the guarded body. (3) Interruption turns persist nothing (non-streamed); streamed saves follow the separate persistence gate (see streaming-persistence-gates.md). (4) Usage projection is span-type dispatch (see turn-span-pairing-parity.md) — this capsule owns the boundary, not the projection.

**Probe:** `tests/test_agent_tracing.py` — `test_task_and_turn_spans_export_aggregate_usage` (:134, exact turn-span usage dict on the happy path), `test_resumed_run_task_span_usage_is_run_local_delta` (:427) and `test_resumed_streaming_run_task_span_usage_is_run_local_delta` (:857, run-local deltas on resumed runs); `tests/test_agent_runner_streamed.py` guardrail-timing suite (tripped input guardrail still unwinds through the streamed finally).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "turn span snapshot usage finally persist session items after turn interruption", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the strict create→start→try/finally window with snapshot-delta usage export — it makes partial-usage-on-failure automatic and impossible to forget. Adapt the persistence ordering to your store: keep "interruption turns persist nothing" and "streamed saves inside the turn, bookkeeping after". Omit the resumed-run `_current_turn_persisted_item_count` bookkeeping if you have no resume protocol. Coverage caveat: MCP absent this pass; Retrieve block is the canonical shape, not an executed call; all citations line-verified by grep against HEAD fe45b415ee05.
