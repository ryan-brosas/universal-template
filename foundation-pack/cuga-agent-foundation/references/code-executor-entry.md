<!-- capsule-v2 -->
# CodeExecutor — the single enforcement point where every tool enters generated code, plus mode-forcing overrides

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** A code-mode agent charges tool calls against a budget, but tools reach generated code from many registration sites (registry, MCP providers, plain python tools, runtime filesystem/shell, delegation). Where do you enforce "every callable in the namespace is charged exactly once" without a new tool silently escaping the budget?

## The unified entry
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/executors/code_executor.py` (`CodeExecutor.eval_with_tools_async` :111-182, `_eval_with_tools_async_impl` :185-308, charging comprehension :154-159).
**Signature:** `CodeExecutor.eval_with_tools_async(code, _locals, state, thread_id=None, apps_list=None, mode=None, plan=None, variable_manager=None) -> tuple[result, new_vars]`.
**Data Shape:** `mode: 'local'|'e2b'|'opensandbox'|None`; returns `(execution result string incl. variables summary, dict of captured new variables)`.

### Decisive source
```python
# code_executor.py:142-164 — the single enforcement point
# Every tool ... reaches generated code through this namespace, on both the
# CugaLite and supervisor graphs. Charging here rather than at each
# registration site means a newly added tool cannot silently escape the budget.
_locals = {
    key: counted_tool_call(value)
    if inspect.iscoroutinefunction(value) and not key.startswith('_')
    else value
    for key, value in _locals.items()
}
ToolCallTracker.seed_block_budget()   # fresh per-block budget, breaks tight loops early

# code_executor.py:207-212 — local-forcing overrides AFTER plan/settings resolution
if len(code_lines) <= 3 and 'await find_tools' in code:
    mode = 'local'
if skills_on and 'load_skill' in code:
    mode = 'local'
```

**Flow:** snapshot `original_keys` → wrap every coroutine-function value (not `_`-prefixed) in `counted_tool_call` → seed block budget → set/reset a contextvar relaxed-execution token around the impl → resolve mode (`plan.python_backend == 'e2b'` else legacy `settings.e2b_sandbox`) → force local for ≤3-line `find_tools` snippets and skill `load_skill` blocks (control tools must run in-process; they'd have no remote transport) → `SecurityValidator.validate_imports` then `validate_wrapped_code` → execute via E2B or LocalExecutor → on exception format error with available-tools list → filter new variables through the pipeline below → trim output to `execution_output_max_length` and append the variables summary.
**Invariant:** Only coroutine functions are charged — every real tool is async by this point (`make_tool_awaitable`), while plain callables carried in `_locals` are *variables* from earlier blocks and must stay uncounted. Names starting with `_` are internal injections and never charged or exported. The block budget is seeded here (once per executed code block) so `max_tool_calls_per_block` hands control back while the run budget is still spendable.
**Probe:** direct tests `executors/tests/test_run_tool_call_cap.py::test_registry_backed_tool_is_charged_once_not_twice`, `::test_tools_that_bypass_the_registry_are_capped`, `executors/tests/test_code_executor.py::test_mode_auto_detection` (:553), `::test_generated_exit_ends_the_block_not_the_runtime`.

### The new-variable pipeline (what survives a block)
After execution, `new_vars` passes through an ordered ladder in `_eval_with_tools_async_impl`: `VariableUtils.filter_new_variables(_locals, original_keys, always_include_keys={'result','results','output','outputs'})` → pop injected `_internal_re` → `strip_todo_confirmation_only_vars` (skills only) → `strip_tools_output_var(new_vars, code)` (drops find_tools discovery markdown — turn-only) → `reorder_variables_by_print` (printed vars moved last) → `limit_variables_to_keep(keep_last_n)` → omit find_tools listing markdown by content sniff → `format_execution_output(result)` trims to max length → `add_variables_to_manager(..., skip_summary_keys={'todos'})` stores vars and appends a "New Variables Created / Updated" summary to the result.

**Invariant (pipeline):** new-key detection is diff-based against `original_keys`, but the four result-shaped keys are re-included even when reassigned so updated values propagate. Non-serializable values are dropped (debug-logged), never crash the run.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "eval_with_tools_async counted_tool_call seed_block_budget format_execution_output", limit: 10 });
```

## Verdict
Adopt the charge-at-the-namespace-boundary pattern (one enforcement point beats per-site accounting), coroutine-only charging with underscore exclusion, the control-tool local-forcing override, and the ordered variable-capture ladder. Adapt allowed-import lists, output-trim limits, and keep-last-N defaults to host. Omit benchmark-mode fake-datetime plumbing unless you reproduce AppWorld-style evals.
