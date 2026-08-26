<!-- capsule-v2 -->
# Result-accumulation PRE/POST pair — how do you record duration and args for a tool call when they're only known at opposite ends?

**Source:** pipeshub-ai Apache-2.0 @ `main` (pin `6850972`); Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** POST_TOOL_USE knows status/duration but not start time or raw input — how does one entry get both halves?

## Metadata stash carried by tool_use_id
**Path/Symbol:** `backend/python/app/agents/agent_loop/hooks/result_accumulation.py:32-60` (`stash_tool_call_metadata` wired PRE_TOOL_USE `factory.py:921`; `result_accumulation` POST :922).
**Signature:** `stash_tool_call_metadata(ctx: ToolCallContext, next_fn)`; `result_accumulation(context) -> Middleware[ToolResultContext]`.
**Data Shape:** appends to `context.tool_state["all_tool_results"]` entries EXACTLY `{tool_name, result, status, tool_id, args, duration_ms}` — the shape Phase 6's RespondPipeline already consumes (nodes.py), so downstream needs zero changes.

### Decisive source
```python
async def stash_tool_call_metadata(ctx: ToolCallContext, next_fn: "Next") -> None:
    """PRE_TOOL_USE: records start time + args for the matching POST hook."""
    ctx.metadata["_result_accum_started_at"] = time.perf_counter()
    ctx.metadata["_result_accum_args"] = dict(ctx.tool_input)
    await next_fn()
...
started_at = ctx.metadata.get("_result_accum_started_at")
duration_ms = (time.perf_counter() - started_at) * 1000 if started_at is not None else 0.0
...
entry: dict[str, Any] = {
    "tool_name": tool_name,
    "result": output.data if output.success else f"Error: {output.error}",
    "status": "success" if output.success else "error",
```

**Flow:** PRE stashes perf_counter + a COPY of tool_input into ctx.metadata → executor carries metadata onto the matching ToolResultContext via the shared `tool_use_id` → POST awaits next_fn then appends the merged entry.
**Invariant:** reproduce the legacy entry shape rather than inventing a new one — schema compatibility is the whole point. The PRE copy (`dict(ctx.tool_input)`) guards against later mutation of the input mapping. Errors are stored as `"Error: {error}"` strings in the result field with status="error", matching what RespondPipeline expects.

### Direct test
**Probe:** `tests/unit/agents/adapter/test_hooks.py::TestResultAccumulation.test_stash_and_accumulate_success` :152, `.test_accumulate_failure_formats_error_message` :173, `.test_multiple_calls_append_in_order` :186. Execute: `/tmp/psh17venv/bin/python -m pytest "tests/unit/agents/adapter/test_hooks.py::TestResultAccumulation" -q` (3 passed at pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "stash_tool_call_metadata result_accumulation all_tool_results duration_ms", limit: 4, fields: ["signature", "name", "file"] });
// resolves hooks/result_accumulation.py symbols + TestResultAccumulation tests
```

## Verdict
Adopt the metadata-stash bridge whenever a two-phase hook pair must recombine pre-execution facts with post-execution outcomes; adopt exact-shape compatibility as an explicit goal. Adapt field names to your downstream consumer. Omit PipesHub's specific legacy shape.
