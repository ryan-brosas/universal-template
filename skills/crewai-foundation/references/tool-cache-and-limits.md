<!-- capsule-v2 -->
# Tool cache + usage limits — when is a repeated tool call served from cache, and how is a per-tool call budget enforced?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** What are the cache key rules, the opt-in gating, the failure-exclusion rule, and the max_usage_count error contract?

## CacheHandler / ToolsHandler / max_usage_count gate
**Path/Symbol:** `lib/crewai/src/crewai/agents/cache/cache_handler.py:10-60`, `agents/tools_handler.py:15-60`, usage gate `experimental/agent_executor.py:1961-1968` + `:2076-2085`, parallelism veto `_should_parallelize_native_tool_calls` `:1908-1909`.
**Signature:** `CacheHandler.add(tool, input, output)` / `.read(tool, input) -> Any | None`; key = f-string `f"{tool}-{input}"` with `input = json.dumps(args_dict) if args_dict else ""`.
**Data Shape:** RWLock-protected dict (multiple readers OR one writer, writers-prioritized Condition). Cache exists on `tools_handler.cache` ONLY when opted in.

### Decisive source
```python
# cache_handler.add — declared failures never enter the cache:
# "Declared failures are never stored: replaying one would make a transient
#  error permanent for the rest of the run, and every later hit would
#  re-report a call that did not run."
if isinstance(output, ToolFailure):
    return
with self._lock.w_locked():
    self._cache[f"{tool}-{input}"] = output

# executor single-call worker:
max_usage_reached = (original_tool and original_tool.max_usage_count is not None
                     and original_tool.current_usage_count >= original_tool.max_usage_count)
...
elif max_usage_reached:
    result = (f"Tool '{func_name}' has reached its usage limit of "
              f"{original_tool.max_usage_count} times and cannot be used anymore.")
    tool_failure = ToolFailure(message=result,
                               reason=ToolFailureReason.USAGE_LIMIT)
```

**Flow:** Read cache BEFORE execution (hit → format via `format_native_tool_output_for_agent`, still `detect_tool_failure(cached_result)` so cached declared-failures surface); miss → execute → ask the tool's own `cache_function(args, result)` for consent → store RAW result. Write-side symmetric gate in `ToolsHandler.on_tool_use` skips caching the CacheTool itself (no recursive cache entries). Opt-in wiring (`agent/core.py:_setup_agent_executor`): standalone agents get a cache only with constructor `cache=True`/`cache_handler=`; crew agents additionally share the crew handler under `Crew(cache=True)`; "Without an opt-in, repeated tool calls with identical arguments always re-execute the tool — the safe default for live-data and state-mutating tools." A copy() records `_constructor_cache_opt_in` BEFORE crew wiring so copies don't become cachers by accident.
**Invariant:** Any tool carrying `max_usage_count` also vetoes PARALLEL batch execution (order-sensitive counter). The usage-limit message IS delivered to the model as a normal tool result AND recorded as a USAGE_LIMIT failure so policy/policy-aware UIs treat it as a failure while the LLM can replan.
**Probe:** `grep -n 'isinstance(output, ToolFailure)' lib/crewai/src/crewai/agents/cache/cache_handler.py` → line 40; behavior pinned in `tests/tools/test_tool_failure.py` per-path suites and native-execution tests exercising `from_cache`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "CacheHandler read add tools_handler cache", limit: 6, detail: "ids" });
```

## Verdict
Adopt raw-value caching with per-tool consent callbacks, failure exclusion, and opt-in-by-default; adapt key format if you need namespacing (add scope prefix — do NOT hash away debuggability); omit RWLock only for single-threaded hosts.
