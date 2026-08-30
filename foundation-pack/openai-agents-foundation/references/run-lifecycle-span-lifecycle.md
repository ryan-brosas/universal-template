<!-- capsule-v2 -->
# Run-lifecycle span lifecycle — how do task/turn/agent/handoff spans get created, paired, errored, and finished across normal, handoff, and exception teardown?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** Which span is created when, which span receives which error or usage payload, and what must a porter replicate so every teardown path leaves a closed, correctly-parented span tree?

## Task span: created before setup, closed on every exit
**Path/Symbol:** `src/agents/run.py:` :786–790 (creation), :956–961 (setup-failure teardown), :2188–2195 (outer finally); `src/agents/run_internal/run_loop.py:` :905–907, :1171, :2016 (streamed twins).
**Signature:** `task_span(name=trace_workflow_name)` guarded by `include_task_and_turn_spans(run_config.tracing)`; usage attached via `attach_usage_to_span(current_task_span, usage_delta(task_usage_start, context_wrapper.usage))`.
**Data Shape:** `task_usage_start = snapshot_usage(context_wrapper.usage)` captured immediately after creation; the delta at close is run-local, so a resumed run's task span carries only the resumed run's usage.

### Decisive source
```python
current_task_span = task_span(name=trace_workflow_name) if use_task_and_turn_spans else None
if current_task_span is not None:
    current_task_span.start(mark_as_current=True)
task_usage_start = snapshot_usage(context_wrapper.usage)
...
except BaseException:
    if current_task_span is not None:
        attach_usage_to_span(current_task_span, usage_delta(task_usage_start, context_wrapper.usage))
        current_task_span.finish(reset_current=True)
    raise
```

**Flow:** task span starts before sandbox/setup work → if setup itself raises, the first `except BaseException` attaches the (likely zero) delta, finishes the span with `reset_current=True`, and re-raises — so the span tree never leaks an open root and a subsequent sibling span parents correctly to the trace → the outer `finally` (after success or a handled run exception) repeats the attach+finish pair after agent-span finish, model cleanup, sandbox memory enqueue, and computer disposal.
**Invariant:** the task span is finished exactly once on every exit path; usage is delta-based from a pre-run snapshot (resumed runs do not inherit prior-run tokens); `finish(reset_current=True)` always precedes `raise`.
**Probe:** `tests/test_agent_tracing.py::test_task_span_resets_current_span_if_run_setup_fails` (:317 pins root-level parent reset after setup failure), `::test_resumed_run_task_span_usage_is_run_local_delta` (:427 pins run-local delta on resume).

## Agent span: lazy, per-agent, handoff-closed
**Path/Symbol:** `src/agents/run.py:` :1451–1463 (lazy creation), :1400–1402 / :2096–2097 (handoff close, non-streamed + streamed), :1466–1470 (max-turns error attach), :2123–2146 (generic error attach + RunErrorDetails).
**Signature:** `agent_span(name=current_agent.name, handoffs=[], tools=[], output_type=output_type_name)` where `output_type_name` comes from the resolved output schema or `"str"`.
**Data Shape:** one live `current_span: Span[AgentSpanData] | None`; `None` means "next turn creates one for the then-current agent".

### Decisive source
```python
if current_span is None:
    output_type_name = (get_output_schema(execution_agent).name()
                        if (output_schema := get_output_schema(execution_agent)) is not None else "str")
    current_span = agent_span(name=current_agent.name, handoffs=[], tools=[], output_type=output_type_name)
    current_span.start(mark_as_current=True)
...
# NextStepHandoff:
current_span.finish(reset_current=True)
current_span = None
should_run_agent_start_hooks = True
```

**Flow:** the agent span is created lazily just before the first model call of a new agent (not at run start) → on a handoff the current span is finished and nulled so the next agent gets a fresh span → terminal errors attach to the CURRENT agent's span: max-turns via `_error_tracing.attach_error_to_span(current_span, SpanError("Max turns exceeded", ...))`, arbitrary run exceptions via `attach_generic_agent_error` with the redaction-policy branch (`_is_error_data_redacted` → detach traceback instead of attach), and `AgentsException` additionally gains `RunErrorDetails` for later introspection.
**Invariant:** exactly one open agent span at any time; a handoff never leaves two open agent spans; error attachment never alters which exception the run raises.
**Probe:** `tests/test_agent_tracing.py::test_agent_span_uses_resolved_tool_name_collision_view` (:76 pins one agent span with resolved tools/handoffs), max-turns + error-attach cases in the same file.

## Turn + handoff spans
**Path/Symbol:** `src/agents/run_internal/run_loop.py:` :1734–1784 (turn span around `run_single_turn_streamed`); `src/agents/run_internal/turn_resolution.py:` :578–601 (`handoff_span`).
**Signature:** `turn_span(turn=current_turn, agent_name=current_agent.name)`; `with handoff_span(from_agent=public_agent.name) as span_handoff:`.
**Data Shape:** turn spans parent to the agent span; `span_handoff.span_data.to_agent` is set only after `on_invoke_handoff` succeeds.

### Decisive source
```python
turn_usage_start = snapshot_usage(context_wrapper.usage)
current_turn_span = turn_span(turn=current_turn, agent_name=current_agent.name) if use_task_and_turn_spans else None
...
finally:
    if current_turn_span is not None:
        attach_usage_to_span(current_turn_span, usage_delta(turn_usage_start, context_wrapper.usage))
        current_turn_span.finish(reset_current=True)
```

**Flow:** each streamed turn snapshots usage, opens a turn span, runs the turn, and in a `finally` attaches the turn delta and finishes — mirroring the task-span pattern one level down → the handoff span wraps the single-winner handoff invocation: `to_agent` recorded after the target resolves, and a `SpanError("Multiple handoffs requested", {requested_agents})` is SET (not raised) when losers existed, so arbitration history lives on the span while the run itself proceeds with the winner.
**Invariant:** turn usage is per-turn delta, never cumulative; a multi-handoff conflict is recorded as span evidence without changing the single-winner outcome.
**Probe:** `tests/test_agent_tracing.py::test_task_and_turn_spans_export_aggregate_usage` (:134 pins exact per-turn usage dicts, parent ids, and task metadata absence), handoff arbitration span cases in `tests/test_handoffs.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "task_span agent_span turn_span finish reset_current usage_delta", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the snapshot→delta→attach-in-finally pattern at every span granularity and the lazy per-agent span with handoff-closed lifecycle. Adapt span types/parenting to your tracing backend. Omit the redaction-policy traceback detach only if your host has no sensitive-data trace mode. Coverage caveat: MCP not connected this pass; direct source+test reading at verified HEAD.
