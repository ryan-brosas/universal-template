<!-- capsule-v2 -->
# Parallel tool fan-out — how are multiple tool calls executed concurrently without corrupting agent state?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** When a ToolCallingAgent receives several tool calls in one message, what runs in parallel, what stays serial, and why is `copy_context()` load-bearing?

## Threaded execution, deterministic memory
**Path/Symbol:** `src/smolagents/agents.py:ToolCallingAgent.process_tool_calls` (:1361-1442), `_step_stream` final-answer guards (:1335-1359), `execute_tool_call` (:1453-1502), `_substitute_state_variables` (:1444-1451).
**Signature:** `process_tool_calls(chat_message, memory_step) -> Generator[ToolCall | ToolOutput]`; single-call fast path bypasses the executor entirely.
**Data Shape:** Calls keyed by tool_call id into `parallel_calls: dict[str, ToolCall]`; outputs collected into `outputs: dict[id, ToolOutput]`; memory records sorted by id (`memory_step.tool_calls = [parallel_calls[k] for k in sorted(...)]`) and observations concatenated in that same sorted order.

### Decisive source
```python
# :1426-1434 — parallel branch:
with ThreadPoolExecutor(self.max_tool_threads) as executor:
    futures = []
    for tool_call in parallel_calls.values():
        ctx = copy_context()                       # snapshot ContextVars per call
        futures.append(executor.submit(ctx.run, process_single_tool_call, tool_call))
    for future in as_completed(futures):
        tool_output = future.result()
        outputs[tool_output.id] = tool_output
        yield tool_output
```

**Flow:** All ToolCalls yielded FIRST (serially, so streaming UIs see the intent), then execution: 1 call → inline; >1 → ThreadPoolExecutor with per-future `copy_context().run` so context-local state (logging bindings, tracing spans) doesn't bleed across concurrent tools. Final-answer arbitration happens in `_step_stream`: a final answer among >1 total calls raises `AgentExecutionError`; two final answers raise `AgentToolExecutionError`; a string result naming an existing state variable is dereferenced through `self.state`. Managed agents are invoked WITHOUT `sanitize_inputs_outputs=True` (they re-template the task); plain tools always get sanitization (AgentImage/AgentAudio unwrap/wrap). Errors inside a tool become AgentToolExecutionError with retry-coaching text; managed-agent failures get team-member phrasing instead (:1492-1496).
**Invariant:** Concurrency applies ONLY to side-effectful execution; memory writes happen after all outputs exist and in sorted-id order, so replay/logs are deterministic regardless of completion order. Dropping `copy_context()` produces cross-talk only under real concurrency — the classic silent porting bug this pattern exists to prevent.
**Probe:** `tests/test_agents.py::test_process_tool_calls` (:2065+, parametrized expected_observations ordering), `test_toolcalling_agent_final_answer_cannot_be_called_with_parallel_tool_calls` (:1816+). Live: build ChatMessage with two tool_calls → observe yields ordered ToolCalls then ToolOutputs as they complete, memory.observations in id order.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "process_tool_calls ThreadPoolExecutor copy_context parallel", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt yield-intent-first / execute-in-threads / record-sorted structure. Adapt pool sizing (`max_tool_threads=None` → interpreter default) and the state-variable dereference if your host lacks a shared state dict. Omit the managed-agent vs tool sanitize asymmetry only if you have no sub-agent concept.
