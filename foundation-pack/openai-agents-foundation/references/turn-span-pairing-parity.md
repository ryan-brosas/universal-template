<!-- capsule-v2 -->
# Turn-span pairing parity — is the streamed/non-streamed turn-span lifecycle identical, and where does usage projection diverge?

**Source:** openai-agents-python MIT `main@fe45b415ee05`; Codebase Memory `openai-agents-python`. **Question:** A porter wiring per-turn tracing must know whether the streamed and non-streamed runners create/finish turn spans the same way, and why exported turn usage lacks request counts while task usage has them.

## Turn-span create/finish twins
**Path/Symbol:** `src/agents/run.py:_run_streamed_impl` turn block (:1615–1630 create, :1753–1760 finally) and `src/agents/run_internal/run_loop.py:run_single_turn_streamed` caller loop (:1736–1746 create, :1779–1784 finally); helpers in `src/agents/run_internal/agent_runner_helpers.py` (`snapshot_usage` :76, `usage_delta` :97, `attach_usage_to_span` :123).
**Signature:** `turn_span(turn: int, agent_name: str) -> Span[TurnSpanData]`; `attach_usage_to_span(span: Span[Any] | None, usage: Usage) -> None`.
**Data Shape:** `turn_usage_start = snapshot_usage(context_wrapper.usage)` taken BEFORE span creation; the finally block computes `usage_delta(turn_usage_start, context_wrapper.usage)` and attaches it. Span creation is gated on `include_task_and_turn_spans(run_config.tracing)` which defaults True (`tracing/config.py` :16: `config is None or config.get("include_task_and_turn_spans", True)`).

### Decisive source
```python
# identical in run.py (non-streamed) and run_loop.py (streamed)
turn_usage_start = snapshot_usage(context_wrapper.usage)
current_turn_span = (
    turn_span(turn=current_turn, agent_name=current_agent.name)
    if use_task_and_turn_spans else None
)
if current_turn_span is not None:
    current_turn_span.start(mark_as_current=True)
try:
    ...  # run_single_turn / run_single_turn_streamed
finally:
    if current_turn_span is not None:
        attach_usage_to_span(
            current_turn_span,
            usage_delta(turn_usage_start, context_wrapper.usage),
        )
        current_turn_span.finish(reset_current=True)
```

**Flow:** snapshot usage → create turn span (turn number + agent name) → start as current → run the whole turn → finally: attach usage delta → finish with reset_current. The finally runs on every exit including exceptions, so a failed turn still reports its partial usage.
**Invariant:** pairing is create-inside-try/finish-in-finally with a pre-turn snapshot; the delta is turn-local, never cumulative; disabling `include_task_and_turn_spans` removes BOTH task and turn spans (agent/generation spans remain).
**Probe:** `tests/test_agent_tracing.py::test_task_and_turn_spans_export_aggregate_usage` (two-turn run: task span usage = sum of both turns incl. requests/total_tokens; each turn span usage = per-turn delta WITHOUT requests/total_tokens; turn parent = agent span, generation parent = turn span); `::test_task_and_turn_spans_can_be_disabled` and `::test_task_and_turn_spans_can_be_explicitly_enabled` (the tracing-dict gate).

## Usage projection dispatch (the real divergence)
**Path/Symbol:** `src/agents/run_internal/agent_runner_helpers.py:attach_usage_to_span` (:123–156).
**Signature:** dispatches on `span.span_data.type`: `"turn"` → `turn_usage_to_span_data`, `"task"` → `task_usage_to_span_data`, anything else → `metadata["usage"] = total_usage_to_span_metadata(usage)`.
**Data Shape:** zero-guard first: if span is None or every usage field (requests, input, output, total, cached, cache_write, reasoning) is 0, attach nothing. Turn exports carry `{input_tokens, output_tokens, cached_input_tokens, cache_write_input_tokens}` only; task exports add `requests` and `total_tokens`.

### Decisive source
```python
if span is None or (usage.requests == 0 and usage.input_tokens == 0
        and usage.output_tokens == 0 and usage.total_tokens == 0
        and cached_tokens == 0 and cache_write_tokens == 0 and reasoning_tokens == 0):
    return
if span.span_data.type == "turn":
    span.span_data.usage = turn_usage_to_span_data(usage)
    return
if span.span_data.type == "task":
    span.span_data.usage = task_usage_to_span_data(usage)
    return
metadata = dict(getattr(span.span_data, "metadata", None) or {})
metadata["usage"] = total_usage_to_span_metadata(usage)
span.span_data.metadata = metadata
```

**Flow:** the SAME `usage_delta` object reaches all span kinds; only the projection differs. A porter who copies the task-span export shape onto turn spans will emit fields the turn schema never had.
**Invariant:** turn spans never expose request counts or totals; the zero-delta turn attaches nothing (a turn with no model calls leaves no usage key).
**Probe:** the same `test_task_and_turn_spans_export_aggregate_usage` asserts the exact per-span export dicts (turn dicts lack `requests`/`total_tokens`; the task dict has them).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "attach_usage_to_span turn_span usage_delta", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the identical create/finally pairing and the pre-turn snapshot-delta pattern for any streamed/non-streamed runner twin. Adopt the span-type-dispatched projection with the zero-guard. Adapt the three projection shapes to your own span schema. Omit nothing here — the pairing is fully portable. Coverage caveat: MCP not connected this pass; all citations verified by direct source+test reads at fe45b415ee05 (grep -n line anchors re-checked before writing).
