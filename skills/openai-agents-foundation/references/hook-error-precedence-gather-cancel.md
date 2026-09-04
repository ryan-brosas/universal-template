<!-- capsule-v2 -->
# Hook error precedence under gather-with-cancel — when parallel tools race a failing lifecycle hook, which failure surfaces and what happens to siblings?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** In a concurrent tool batch, how are run/agent hooks paired, and why does a hook exception beat a sibling's cancellation?

## Cancel-and-drain gather + per-tool hook sites
**Path/Symbol:** `src/agents/util/_asyncio_tasks.py:` `gather_with_cancel` (:93–114), `_consume_future_exception` (:18–23); pairing sites in `src/agents/run_internal/tool_execution.py:` `_execute_single_tool_body` (:1992–2042 on_tool_start), `_invoke_tool_and_run_post_invoke` (:2050–2166 on_tool_end), wrapper `_run_single_tool` (:1785–1856 UserError wrapping).
**Signature:** `gather_with_cancel(*awaitables, on_child_failure: Callable[[], None] | None = None) -> tuple[Any, ...]`.
**Data Shape:** each hook site gathers exactly two awaitables — run-level hooks and agent-level hooks (noop coroutine when agent has none); the batch level uses the same helper across per-tool tasks.

### Decisive source
```python
tasks = [asyncio.ensure_future(a) for a in awaitables]
gather_future = asyncio.gather(*tasks)
gather_future.add_done_callback(_consume_future_exception)
try:
    await asyncio.wait((gather_future,))
    try:
        return tuple(gather_future.result())
    except BaseException:
        if on_child_failure is not None:
            on_child_failure()
        raise
except BaseException:
    for task in tasks:
        if not task.done():
            task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    raise
...
# _run_single_tool:
except Exception as e:
    ...attach SpanError(message="Error running tool", data={"tool_name": ...})...
    if isinstance(e, AgentsException):
        raise
    raise UserError(f"Error running tool {func_tool.name}: {e}") from e
```

**Flow:** per tool — input guardrails → `gather_with_cancel(run_hooks.on_tool_start ∥ agent_hooks.on_tool_start)` → invocation spawned as a tracked task → cancellation handling (outer-task teardown re-raises raw; ordinary cancel goes through the failure formatter) → output guardrails → output item built AND committed to results/committer BEFORE the end-hooks run → `gather_with_cancel(run_hooks.on_tool_end ∥ agent_hooks.on_tool_end)` → any hook Exception bubbles into `_run_single_tool`'s `except Exception` and leaves as `UserError("Error running tool <name>: …")`; at every nesting level the first child exception cancels remaining siblings, drains them with `return_exceptions=True` (so no "exception never retrieved"), then re-raises the winner.
**Invariant:** a real hook/guardrail failure always wins over a sibling's CancelledError because it is the exception that lands first in the shared gather; cancellation during turn teardown propagates unwrapped (`CancelledError` is BaseException, never converted by the `except Exception` wrapper); end-hook failure cannot un-commit an already-recorded tool output item.
**Probe:** `tests/test_run_step_execution.py::test_multiple_tool_calls_surface_hook_failure_over_sibling_cancellation` (:1025 asserts `UserError match="Error running tool ok_tool: hook boom"` while cancel_tool self-raises CancelledError), `tests/test_asyncio_tasks.py::test_gather_with_cancel_reports_child_failure_before_cancelling_siblings` (:12), `::test_gather_with_cancel_does_not_report_parent_cancellation_as_child_failure` (:43).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "openai-agents-python", qualified_name: "openai-agents-python.src.agents.util._asyncio_tasks.gather_with_cancel" });
await mcp.codebase_memory.get_code_snippet({ project: "openai-agents-python", qualified_name: "openai-agents-python.src.agents.run_internal.tool_execution._FunctionToolBatchExecutor._invoke_tool_and_run_post_invoke" });
```

## Verdict
Adopt gather-with-cancel semantics (first child failure wins, siblings cancelled+drained, parent cancellation stays anonymous) wherever parallel side effects share fate; adopt hook-pair concurrency so one slow hook cannot serialize the batch; adopt commit-before-end-hooks so observability survives hook crashes. Adapt error wrapping types to your exception taxonomy. Omit teardown-vs-failure discrimination only if your runner has no cooperative cancellation. Coverage: no_recorded_issue @ gen 2026-08-24T14:05:06Z.
