<!-- capsule-v2 -->
# Barrier-segmented parallel execution — how do tools run concurrently without breaking ordering, event modes, or sibling cleanup?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** How does a step execute N tool calls with parallelism while keeping history in emission order, honoring per-tool barriers, and not orphaning sibling tasks on failure?

## Segment-by-barrier scheduler
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_tool_execution.py:_segment_by_barriers` (232–251), `_call_tools` (736–860); mode source `tool_manager.py:ToolManager.parallel_execution_mode` (170–185) + `_parallel_execution_mode_ctx_var` (44–46).
**Signature:** `_segment_by_barriers(indices: list[int], *, is_barrier: Callable[[int], bool]) -> list[list[int]]`; run-scoped mode `Literal['parallel', 'sequential', 'parallel_ordered_events']`; per-tool barrier = `tool_def.sequential`.
**Data Shape:** Parts are staged per-index (`tool_parts_by_index`, `user_parts_by_index`, deferred maps) and appended to history only after the whole walk, sorted by index — completion order never leaks into message order.

### Decisive source
```python
# _tool_execution.py:232-251 — each barrier becomes its own 1-element segment
def _segment_by_barriers(indices, *, is_barrier):
    segments, current = [], []
    for i in indices:
        if is_barrier(i):
            if current:
                segments.append(current); current = []
            segments.append([i])
        else:
            current.append(i)
    if current:
        segments.append(current)
    return segments

# :787-797 — a sequential=True tool runs alone; 'sequential' mode makes EVERY tool a barrier
segments = _segment_by_barriers(
    list(range(len(tool_calls))),
    is_barrier=lambda i: global_sequential or self.tool_manager.is_sequential(tool_calls[i]),
)
```

**Flow:** Split indices into segments around barriers → within a segment launch `asyncio.create_task` per call (task names = tool names) → drain by `FIRST_COMPLETED` (events stream as they finish) or wait-all then replay in index order (`parallel_ordered_events`) → single-call/barrier segments run inline → `finally` prunes duplicate reveals and extends `output_parts` in sorted-index order even on exception. Cancellation path uses `cancel_and_drain(*tasks)` so siblings settle instead of becoming orphaned tasks; the same guard catches non-CancelledError BaseExceptions.
**Invariant:** History append order is emission order, decoupled from completion order — dedupe of `ToolAvailabilityDeltaPart` happens at assembly time (not per-task) precisely because parallel siblings race for the delta. The prune is non-idempotent: a second pass would see every name as already discovered and drop deltas it just kept. A `sequential=True` tool no longer serializes the WHOLE batch (v1 behavior) — it's one barrier among segments.
**Probe:** `tests/test_agent.py::TestMultipleToolCalls` (:4702 class docstring requires mirroring in `tests/test_streaming.py::TestMultipleToolCalls`) pins ordering across strategies; `tests/test_concurrency.py` covers the concurrency primitives.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_segment_by_barriers _call_tools parallel_execution_mode cancel_and_drain", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt segment-around-barrier scheduling, assembly-time ordering + dedupe, and cancel-and-drain cleanup; adapt the contextvar mode switch to your host's run-scoped config; omit `parallel_ordered_events` if your consumers tolerate completion-order events. Caveat: none — full ranges read at HEAD this session.
