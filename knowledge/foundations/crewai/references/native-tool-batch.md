<!-- capsule-v2 -->
# Native tool-call batch execution — when do parallel calls run, and how do result_as_answer and failures short-circuit?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** How does one assistant message fan out to N tool executions while keeping result_as_answer semantics and thread-safe context?

## execute_native_tool + _should_parallelize_native_tool_calls
**Path/Symbol:** `lib/crewai/src/crewai/experimental/agent_executor.py:1693-1878` (`execute_native_tool`), `:1880-1911` (`_should_parallelize_native_tool_calls`), single-call body `_execute_single_native_tool_call` `:1913-2146`.
**Signature:** `def execute_native_tool(self) -> Literal["native_tool_completed", "tool_result_is_final"]`.
**Data Shape:** Consumes `state.pending_tool_calls` (list of provider tool-call objects); emits ONE assistant message with `tool_calls=[{id,type,function:{name,arguments}}]`, then one `role:"tool"` message per result keyed by `tool_call_id`.

### Decisive source
```python
if should_parallelize:
    max_workers = min(8, len(runnable_tool_calls))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_idx = {
            pool.submit(contextvars.copy_context().run,
                        self._execute_single_native_tool_call, tool_call): idx
            for idx, tool_call in enumerate(runnable_tool_calls)}
        ordered_results = [None] * len(runnable_tool_calls)
        for future in as_completed(future_to_idx):
            ...
            except ToolExecutionFailedError:
                # "Cancel the siblings that have not started so they never
                #  run. Ones already in flight cannot be interrupted -- Python
                #  threads are not cancellable"
                pool.shutdown(wait=False, cancel_futures=True)
                raise
            except Exception as e:
                ordered_results[idx] = {...f"Error executing tool: {e}"...}
else:
    # "Execute sequentially so result_as_answer tools can short-circuit
    #  immediately without running remaining calls."
    for tool_call in runnable_tool_calls:
        ... if original_tool.result_as_answer and execution_result.get("tool_failure") is None:
                self.state.current_answer = AgentFinish(
                    thought="Tool result is the final answer", ...)
                return "tool_result_is_final"

def _should_parallelize_native_tool_calls(self, tool_calls) -> bool:
    if len(tool_calls) <= 1: return False
    for tool_call in tool_calls:
        ...resolve original_tool...
        if getattr(original_tool, "result_as_answer", False): return False
        if getattr(original_tool, "max_usage_count", None) is not None: return False
    return True
```

**Flow:** Snapshot+clear pending → build grouped assistant message (raw Gemini `Part` objects preserved via `raw_tool_call_parts`) → choose parallel vs sequential by scanning EVERY call's original tool → execute (parallel results reassembled into ORIGINAL index order before appending) → append per-call tool messages in call order → any single qualifying `result_as_answer` converts to final answer. The single-call worker handles arg JSON parse failure as an INVALID_INPUT ToolFailure dict (never a silent `{}`), cache read/write gated on the tool's own `cache_function`, before/after hooks, usage events with `started_at`, delegation tracking, and `handle_tool_failure` AFTER the finished event so subscribers see the full lifecycle even under a RAISE policy.
**Invariant:** A failed tool must NEVER become the final answer — enforced twice (native path checks `execution_result.get("tool_failure") is None`; shared util `execute_tool_and_check_finality` returns `result_as_answer=tool.result_as_answer and tool_usage.last_failure is None`). Parallel mode requires order-independent tools: any `result_as_answer` or usage-limited tool forces sequential because both have order-sensitive semantics.
**Probe:** `tests/agents/test_agent_executor.py::TestNativeToolExecution.test_execute_native_tool_runs_parallel_for_multiple_calls / test_execute_native_tool_falls_back_to_sequential_for_result_as_answer / test_execute_native_tool_result_as_answer_short_circuits_remaining_calls`; failure-path suite `tests/tools/test_tool_failure.py::TestMalformedArgsOnEveryPath.test_react_path_reports_a_malformed_call` et al.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "execute_native_tool result_as_answer parallel", limit: 6, detail: "ids" });
```

## Verdict
Adopt the parallelism gate + ordered-result reassembly + failure-exclusion-from-final-answer trio; adapt worker count/executor to your runtime; omit `contextvars.copy_context().run` only if your tools need no context propagation (you probably do need it — hooks and collectors are ContextVar-based).
