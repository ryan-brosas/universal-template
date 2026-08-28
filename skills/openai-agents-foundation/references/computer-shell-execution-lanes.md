<!-- capsule-v2 -->
# Computer and local-shell execution lanes — how do non-function tool categories execute, commit outputs incrementally, and survive a resume turn?

**Source:** openai-agents-python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** A porter adding non-function tool categories (computer use, local shell) must know how they are bucketed, filtered on resume, executed, and how their outputs are committed and ordered relative to function results.

## Bucket → filter → plan → execute → commit
**Path/Symbol:** `src/agents/run_internal/run_steps.py:ProcessedResponse` (:117–141) + `ToolRunComputerAction`/`ToolRunLocalShellCall` (:81/:101); `src/agents/run_internal/turn_resolution.py` computer pre-filter (:2357–2362) + `_commit_tool_output` (:2446–2464); `src/agents/run_internal/tool_planning.py:_execute_tool_plan` (:944–1070); `src/agents/run_internal/tool_execution.py:execute_computer_actions` (:2442–2512) / `execute_local_shell_calls` (:2361–2384); `src/agents/run_internal/tool_actions.py:ComputerAction.execute` (:107–200).
**Signature:** `async def _execute_tool_plan(*, plan: ToolExecutionPlan, bindings, hooks, context_wrapper, run_config, parallel: bool = True, tool_output_committer: Callable[[RunItem], None] | None = None) -> tuple[...]`; `async def execute_computer_actions(*, public_agent, actions, hooks, context_wrapper, config, tool_output_committer=None) -> list[RunItem]`.
**Data Shape:** `ProcessedResponse` carries parallel buckets: `functions`, `computer_actions`, `local_shell_calls`, `shell_calls`, `apply_patch_calls`, `custom_tool_calls`, `mcp_approval_requests`, `interruptions`, `function_tools_not_found`. `ToolExecutionPlan` mirrors them post-approval-filtering.

### Decisive source
```python
# resume pre-filter: computer lane is output-exists-only (no approval collector)
pending_computer_actions: list[ToolRunComputerAction] = []
for action in processed_response.computer_actions:
    call_id = _computer_call_id_from_run(action)
    if _computer_output_exists(call_id):   # _has_output_item(call_id, "computer_call_output")
        continue
    pending_computer_actions.append(action)
```
```python
# incremental commit keeps outputs ordered by the call's position in the model response
def _commit_tool_output(item: RunItem) -> None:
    if any(existing is item for existing in committed_tool_outputs):
        return
    committed_tool_outputs.append(item)
    committed_tool_outputs.sort(
        key=lambda output: call_positions.get(
            extract_tool_call_id(getattr(output, "raw_item", None)) or "",
            len(call_positions),
        )
    )
    if run_state is not None:
        run_state._generated_items = [*original_pre_step_items, *committed_tool_outputs]
    _register_tool_call_items(context_wrapper, [item])
```

**Flow:** (1) `process_model_response` buckets model output into typed `ToolRun*` dataclasses; computer actions require a `ComputerTool` in `all_tools` else `ModelBehaviorError("Model produced computer action without a computer tool.")` (:3070–3078); (2) on resume, the computer lane gets ONLY the output-exists pre-filter (idempotence skip) — unlike shell/apply_patch/custom, computer actions have no approval collector; (3) `_build_plan_for_resume_turn` assembles a `ToolExecutionPlan`; (4) `_execute_tool_plan` runs six category executors in one `gather_with_cancel` with a shared `sibling_category_failure` event (`on_child_failure=sibling_category_failure.set`); failure isolation turns on when more than one function run OR any non-function category is present; (5) `execute_computer_actions` runs actions SERIALLY: mark-executed-before-run, pending safety checks must each be acknowledged (`on_safety_check` awaitable-or-plain) or `UserError("Computer tool safety check was not acknowledged")` is raised; (6) `ComputerAction.execute` resolves the computer, fires the `on_tool_start ∥ agent on_tool_start` pair, executes + captures the screenshot, builds a `ComputerCallOutput` (`type="computer_call_output"`, `output={"type": "computer_screenshot", "image_url": data-url}`) wrapped in a `ToolCallOutputItem`, commits it via `tool_output_committer` (incremental, position-ordered, run-state-visible), extracts custom data, then fires the `on_tool_end` pair; errors set a span error with redaction-aware `get_trace_tool_error` and re-raise; (7) `execute_local_shell_calls` delegates serially to `LocalShellAction.execute` with the same committer; (8) back in turn resolution, `_build_tool_result_items` orders function results (each carries `.run_item`) before computer/custom/shell/apply-patch results, and `_make_unique_item_appender` dedupes by object identity.
**Invariant:** Every committed output is registered exactly once (identity check in `_commit_tool_output`), stays ordered by the call's position in the model response (unknown positions sort last via the `len(call_positions)` default), and is visible to `run_state._generated_items` immediately — so an interruption mid-batch never loses or duplicates an already-executed action's output on resume.
**Probe:** `tests/test_computer_action.py::test_execute_invokes_hooks_and_returns_tool_call_output` (:538), `::test_pending_safety_check_acknowledged` (:749); `tests/test_local_shell_tool.py::test_runner_executes_local_shell_calls` (:158), `::test_local_shell_output_survives_run_state_resume` (:232).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "execute_computer_actions _commit_tool_output ToolExecutionPlan sibling_category_failure", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bucket/plan/execute split with a single shared commit callback and position-ordered incremental commits — this is the portable core for any multi-category tool executor. Adapt the serial-vs-parallel choice per category (computer and local shell are deliberately serial; functions batch in parallel). Omit the safety-check acknowledgment ladder only if your computer tool has no safety-check surface. Coverage caveat: MCP not connected this pass; anchors verified by direct reads at HEAD fe45b415.
