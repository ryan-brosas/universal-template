<!-- capsule-v2 -->
# LocalExecutor — timeout/exit evidence recovery: read the still-live frame BEFORE cancelling, never discard partial work

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** An agent executes LLM-generated code blocks with a timeout. When a block stalls on an `await` or calls `exit()`, how do you keep the variables it already computed — instead of returning a bare "timed out" that makes the agent re-run identical code until the step limit?

## The recovery executor
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/executors/local/local_executor.py` (`LocalExecutor.execute` :49-189, `_locals_from_coro` :210-228, `_locals_from_frame` :192-207, `format_error` :230-279, `_unknown_tool_correction` :282-342).
**Signature:** `async execute(wrapped_code, context_locals, timeout=30) -> str`; `format_error(error, available_tools=None, code=None) -> str`.
**Data Shape:** runs `exec(wrapped_code, restricted_globals, exec_locals)` then awaits `exec_locals['_async_main']()` as an `asyncio.Task`; `context_locals.update(...)` mutates the caller's dict in place (the variable-transfer channel).

### Decisive source
```python
# local_executor.py:100-126 — Task + asyncio.wait so the stalled frame survives
task = asyncio.create_task(_run_block())
done, _pending = await asyncio.wait({task}, timeout=timeout)
if not done:
    recovered = self._locals_from_coro(task.get_coro(), "_async_main")
    task.cancel()   # frame is cleared after this — recover FIRST
    ...
    guidance = (
        f"Error during execution: Execution timed out after {timeout} seconds.\n"
        f"This code block started {calls_made} tool call(s) before it was killed; "
        f"{kept_note}"
        "Do NOT rerun the same code — it will time out again. Restructure instead: ..."
    )
    if partial_stdout.strip():
        guidance += f"Partial stdout before the timeout:\n{partial_stdout}"
```
```python
# _locals_from_coro walks cr_await through wrapper coroutines
while coro is not None and id(coro) not in seen:
    frame = getattr(coro, "cr_frame", None)
    ...  # match f_code.co_name == "_async_main", drop "__"-prefixed locals
```

**Flow:** exec under `redirect_stdout(StringIO)` → run `_async_main` as a Task (NOT bare-coroutine `wait_for`, which clears the frame) → three stop paths: **timeout** = recover locals from the suspended coroutine frame *before* cancel, return structured guidance with kept-variable names, block tool-call count, and partial stdout; **SystemExit** (`exit()` in generated code) = caught inside the Task as a `_BlockSystemExit` carrier (so asyncio doesn't re-raise it into the loop), recovered via the exception's traceback frame; **exception** = attach captured stdout to `e.captured_stdout` and re-raise so discovery output from earlier lines still reaches the agent.
**Invariant:** variables computed before a stall are readable only while the frame is live — `wait_for` on a bare coroutine destroys them at cancellation time; recovery must precede `task.cancel()`. `exit()/quit()` in generated code ends the BLOCK, never the runtime: intent honored, pre-exit variables kept, nothing after exit runs. Frame-locals filtering drops dunder-prefixed names so wrapper plumbing never becomes agent state.

## The fabricated-tool-name correction
`format_error` augments a raw `NameError` traceback with a `[tool-name correction]` listing the closest real tool names (`difflib.get_close_matches(missing, available_tools, n=5, cutoff=0.6)`) when AST analysis of `code` shows the missing name is USED like a tool (bare call or assignment-RHS alias) and NOT defined by the code itself (def/class/import/store target). A NameError on a plain variable reference keeps its bare traceback — there the right fix is computing the variable, not re-querying find_tools. With no close match the hint points to `find_tools` without steering toward lookalikes ("similarly named tools can do very different things — delete vs get").

**Invariant (correction):** both usage and definition checks are AST-based, so names inside string literals or comments never count; suppression rules exist because misdirected hints cause retry loops of their own.

**Probe:** direct tests `executors/tests/test_timeout_evidence.py::test_timeout_keeps_variables_computed_before_stall`, `::test_timeout_reports_block_tool_call_count`, `::test_successful_block_unaffected`; `executors/tests/test_code_executor.py::test_unknown_tool_name_gets_correction` (:78), `::test_undefined_variable_keeps_bare_name_error` (:140), `::test_assignment_rhs_fabricated_tool_gets_correction` (:206), `::test_correction_suppressed_for_agent_defined_helper` (:318), `::test_generated_exit_ends_the_block_not_the_runtime` (:568); `executors/tests/test_code_wrapper_freeze.py` for the freeze teardown.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "LocalExecutor _locals_from_coro _BlockSystemExit _unknown_tool_correction get_close_matches", limit: 10 });
```

## Verdict
Adopt Task-not-wait_for execution with pre-cancel frame recovery, the SystemExit-carrier block-end contract, captured-stdout-on-error evidence preservation, and the usage-shaped/AST-gated tool-name correction. Adapt timeout defaults, guidance wording, and the correction cutoff to your model's failure modes. Omit the benchmark fake-datetime branch unless reproducing AppWorld evals.
