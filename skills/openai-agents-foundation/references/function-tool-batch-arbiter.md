<!-- capsule-v2 -->
# Function-tool batch execution + failure arbitration — how does a parallel tool batch cancel, drain, and pick ONE root-cause failure?

**Source:** OpenAI Agents Python MIT `main@fe45b415ee05`; Codebase Memory project `openai-agents-python` (MCP absent this pass — direct source+test reading fallback per AGENTS.md). **Question:** When several function tools run concurrently and one fails (or the parent is cancelled), how does the runtime stop the batch, let in-flight work settle, and surface exactly one root-cause error without leaking background exceptions?

## Batch executor + arbitration helpers
**Path/Symbol:** `src/agents/run_internal/tool_execution.py:` `execute_function_tool_calls` (:2308–2338) → `_FunctionToolBatchExecutor` (:1552–2306); helpers `_FunctionToolFailure` (:181–187), `_FunctionToolTaskState` (:198–203), `_get_function_tool_failure_priority` (:258–265), `_select_function_tool_failure` (:267–284), `_merge_late_function_tool_failure` (:286–305), `_record_completed_function_tool_tasks` (:327–357), `_settle_pending_function_tool_tasks` (:438–486), `_drain_cancelled_function_tool_tasks` (:488–530), `_wait_pending_function_tool_tasks_for_timeout` (:532–554); constants `_FUNCTION_TOOL_CANCELLED_DRAIN_SECONDS = 0.25`, `_FUNCTION_TOOL_CANCELLED_IMMEDIATE_STEP_LIMIT = 64`, `_FUNCTION_TOOL_POST_INVOKE_WAIT_SECONDS = 0.1` (:167–169).
**Signature:** `async def execute_function_tool_calls(*, bindings, tool_runs: list[ToolRunFunction], hooks, context_wrapper, config, isolate_parallel_failures: bool | None = None, sibling_category_failure: asyncio.Event | None = None, tool_output_committer: Callable[[RunItem], None] | None = None) -> tuple[list[FunctionToolResult], list[ToolInputGuardrailResult], list[ToolOutputGuardrailResult]]`.
**Data Shape:** `isolate_parallel_failures` defaults to `len(tool_runs) > 1`; concurrency from `config.tool_execution.max_function_tool_concurrency` (None ⇒ unbounded); per-task `_FunctionToolTaskState{tool_run, order, invoke_task, in_post_invoke_phase}`; results keyed by `id(tool_run)` in `results_by_tool_run`; failure record `{error, order, source: "direct"|"cancelled_teardown"|"post_invoke"}`.

### Decisive source
```python
async def _raise_failure_after_draining_siblings(self, failure):
    cancellable_tasks, post_invoke_tasks = self._partition_pending_tasks()
    self.teardown_cancelled_tasks.update(cancellable_tasks)
    _cancel_function_tool_tasks(cancellable_tasks)
    late_failure, remaining_cancelled_tasks = await self._drain_cancelled_tasks(cancellable_tasks)
    post_invoke_failure, remaining_post_invoke_tasks = await self._wait_post_invoke_tasks(post_invoke_tasks)
    # ... attach loop-level exception reporters to tasks that outlive the batch ...
    merged_failure = _merge_late_function_tool_failure(failure, late_failure)
    merged_failure = _merge_late_function_tool_failure(merged_failure, post_invoke_failure)
    self.pending_tasks = set()
    self.propagating_failure = merged_failure.error
    raise merged_failure.error
```
and the priority/tie-break core:
```python
def _select_function_tool_failure(current_failure, new_failure):
    ...
    if new_priority > current_priority: return new_failure
    if new_priority == current_priority and new_failure.order < current_failure.order:
        return new_failure
    return current_failure
```
with `_merge_late_function_tool_failure` preferring a `post_invoke`-sourced failure over a non-post-invoke one on a priority tie.

**Flow:** executor resolves enabled tools (disabled-but-configured tool ⇒ `ModelBehaviorError`; unlisted tool appended) → `_fill_tool_task_slots` creates `asyncio.Task`s up to concurrency → `_drain_pending_tasks` waits `FIRST_COMPLETED`, records results ordered by `order`, and on the first failure raises after the drain ladder → drain ladder: partition pending into cancellable (not yet post-invoke) vs post-invoke; cancel the first; drain cancelled siblings only while they can still make self-driven progress (progress deadlines via `get_function_tool_task_progress_deadline`, 0.25 s window, 64 immediate-step budget); wait post-invoke siblings 0.1 s so in-flight failures surface; merge late failures into the trigger; attach `_consume_function_tool_task_result` reporters (message differs: cleanup vs post-invoke vs parent-cancelled) to anything still running. Parent cancellation path (`CancelledError` in `execute`) either drains for a sibling-category failure event or cancels everything with parent-cancelled reporting. Per-tool body: function span (sensitive-data-gated input/output), approval ladder in `_maybe_execute_tool_approval` (None ⇒ `function_needs_approval` ⇒ re-query; optional pre-approval input guardrails via `tool_execution.pre_approval_tool_input_guardrails`; still None ⇒ the `ToolApprovalItem` IS the result; False ⇒ rejection item + span error), exactly-once `_mark_tool_invocation_executed` before user code (skipped for nested-agent continuation), input guardrails, `on_tool_start`/`on_tool_end` hooks via `gather_with_cancel`, invoke wrapped in an inner `invoke_task` awaited through `asyncio.shield`; a `CancelledError` inside invoke can be converted by `failure_error_function` into a real output (schema bypassed when SDK-generated and not programmatic); output guardrails run in the post-invoke phase — a rejection marks the run schema-bypassed so the provider receives `function_tool_error_output`; nested agent-tool results are held back until interruptions resolve.

**Invariant:** (1) Exactly one failure propagates; it is the highest-priority (BaseException > Exception > CancelledError), lowest-order, root-cause record — late failures merge in, never mask it. (2) No background task ever dies silently: every task that outlives the batch gets a done-callback that routes its exception to the loop handler with a source-specific message. (3) Post-invoke work (output guardrails, hooks) gets a bounded grace window instead of instant cancellation. (4) `propagating_failure` identity-checks the `CancelledError` so the executor's own raise is re-raised, not double-handled.

**Probe:** `tests/test_run_step_execution.py` — `test_multiple_tool_calls_still_raise_when_sibling_failure_error_function_none` (:626, root-cause UserError propagates), `test_multiple_tool_calls_surface_post_invoke_failure_unblocked_during_settle_turns` (:2035), `test_multiple_tool_calls_surface_sleeping_post_invoke_failure_before_sibling_error` (:2105, widens `_FUNCTION_TOOL_POST_INVOKE_WAIT_SECONDS` to prove the grace window, not scheduling, decides the winner), `test_multiple_tool_calls_do_not_wait_indefinitely_for_sleeping_post_invoke_sibling` (:2175), `test_execute_tool_plan_cancels_sibling_category_on_failure` (:4271), `test_execute_tool_plan_parent_cancellation_interrupts_sibling_failure_drain` (:4542).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "function tool batch executor failure arbitration drain cancelled siblings post invoke", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-lane teardown (cancel non-post-invoke, drain-while-progressing, grace-wait post-invoke) and the priority+order+source failure merge — it is the reusable core. Adapt the progress-deadline mechanism (`get_function_tool_task_progress_deadline`) to your own cancellation vocabulary. Omit the nested agent-tool result holding and schema-bypass bookkeeping if your port has no agent-as-tool or programmatic-output feature. Coverage caveat: MCP absent this pass; Retrieve block is the canonical shape, not an executed call; all citations line-verified by grep against HEAD fe45b415ee05.
