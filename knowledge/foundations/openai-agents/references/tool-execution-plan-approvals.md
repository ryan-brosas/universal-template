<!-- capsule-v2 -->
# ToolExecutionPlan & approval tri-state — how does a turn's tool work get planned, and how does each run resolve to approved / rejected / pending?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** What data structure carries a turn's tool work, and what is the exact resolution order for approval decisions?

## Plan structure + `_collect_runs_by_approval` ladder
**Path/Symbol:** `src/agents/run_internal/tool_planning.py:` `ToolExecutionPlan` (:557–573), `_build_plan_for_fresh_turn` (:619–646) / `_build_plan_for_resume_turn` (:649–682), `_collect_runs_by_approval` (:759–840), `_select_function_tool_runs_for_resume` (:883–941), `_execute_tool_plan` (:944–1101).
**Signature:** `async def _collect_runs_by_approval(runs, *, call_id_extractor, tool_name_resolver, rejection_builder, context_wrapper, approval_items_by_call_id, agent, pending_interruption_adder, needs_approval_checker=None, output_exists_checker=None) -> tuple[list[T], list[RunItem]]`.
**Data Shape:** plan buckets: function_runs, computer_actions, custom_tool_calls, shell_calls, apply_patch_calls, local_shell_calls, pending_interruptions, approved_mcp_responses, mcp_requests_with_callback. Resume plans take pre-filtered buckets and FORCE `local_shell_calls=[]`.

### Decisive source
```python
approval_status = context_wrapper.get_approval_status(tool_name, call_id,
    existing_pending=existing_pending, current_invocation=current_item)
needs_approval = True
if approval_status is None and needs_approval_checker is not None:
    try:    needs_approval = await needs_approval_checker(run)
    except UserError: raise
    except Exception: needs_approval = True        # checker failure ⇒ ask the human
    approval_status = context_wrapper.get_approval_status(...)   # checker may record an answer
if approval_status is False: -> rejection item
elif approval_status is True or not needs_approval: -> execute
else: pending_interruption_adder(existing_pending if existing_pending is not None else current_item)
```
Fresh plans derive all buckets from the processed response; resume plans receive already-selected runs and rebuild only MCP/interruptions. Execution fans ALL six executor families through one `gather_with_cancel` with a shared `sibling_category_failure` event; isolation kicks in when >1 function run OR any parallel cross-category work exists.

**Invariant:** The human-approval question is asked at most once per run per turn (checker runs ONLY when no stored status exists) and its failures degrade to "ask"; rejections become model-visible output items, never exceptions; pending items reuse the EXISTING interruption item when present so UI state stays stable across resumes.

**Probe:** `tests/test_hitl_error_scenarios.py::test_resume_skips_needs_approval_checker_when_status_resolved` (:1502), `test_function_needs_approval_invalid_type_raises` (:905); collision/rebind behavior in `tests/test_tool_name_collision_policy.py` (:51–352).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "collect runs by approval needs approval checker pending interruption", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the plan-bucket + tri-state pattern for multi-kind executors with HITL; adapt bucket taxonomy to your tool kinds; omit the resume/fresh split if your runner has no interruption resume.
