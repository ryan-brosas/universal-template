<!-- capsule-v2 -->
# Resume collector lanes — how are shell/apply_patch/custom approvals collected on resume without duplicating outputs or re-interrupting?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** When a resumed turn contains non-function tool calls (shell, apply_patch, custom), how does one generic collector turn approval state into approved runs, rejection outputs, and pending interruptions — once per call?

## One generic collector, five injected behaviors
**Path/Symbol:** `src/agents/run_internal/tool_planning.py:` `_collect_runs_by_approval` (:759–833); call sites `src/agents/run_internal/turn_resolution.py:` :2364 (shell), :2377 (apply_patch), :2390 (custom); per-type adapters :1318–1459.
**Signature:** `async def _collect_runs_by_approval(runs, *, call_id_extractor, tool_name_resolver, rejection_builder: Callable[[T, str], Awaitable[RunItem] | RunItem], context_wrapper, approval_items_by_call_id, agent, pending_interruption_adder, needs_approval_checker=None, output_exists_checker=None) -> tuple[list[T], list[RunItem]]`.
**Data Shape:** `approval_items_by_call_id` maps call_id → persisted `ToolApprovalItem`; the collector is generic over the run type `T`; rejection builders may be sync or async (resolved with `inspect.isawaitable`).

### Decisive source
```python
call_id = call_id_extractor(run)
if output_exists_checker is not None and output_exists_checker(call_id):
    continue
...
approval_status = context_wrapper.get_approval_status(
    tool_name, call_id,
    existing_pending=existing_pending, current_invocation=current_item)
needs_approval = True
if approval_status is None and needs_approval_checker is not None:
    try:
        needs_approval = await needs_approval_checker(run)
    except UserError:
        raise
    except Exception:
        needs_approval = True
    approval_status = context_wrapper.get_approval_status(...)  # re-query
if approval_status is False:
    rejection_items.append(rejection_builder(run, call_id) ...)  # awaitable-or-plain
elif approval_status is True or not needs_approval:
    approved_runs.append(run)
else:
    pending_interruption_adder(existing_pending if existing_pending is not None else current_item)
```

**Flow:** per run: output-exists skip (idempotence) → build a fresh `ToolApprovalItem` (namespace/origin/lookup_key from the concrete tool) → query approval status with `existing_pending` + `current_invocation` → status `None` consults the type's `needs_approval_checker` then RE-QUERIES status (the checker may register an approval as a side effect) → `False` emits a rejection output, `True`/not-needing approves, undecided re-adds the pending interruption preferring the persisted item → three call sites inject per-type adapters: shell/apply_patch/custom call-id extractors (custom raises `ModelBehaviorError` on missing id), name resolvers, rejection builders (`resolve_approval_rejection_message` + `shell_rejection_item` / `apply_patch_rejection_item`; custom hand-builds a `custom_tool_call_output` dict with `copy_tool_call_caller`), needs-approval evaluators (apply_patch evaluates per operation and short-circuits on the first non-None approval status), and `(type, call_id)` output-exists checkers against the resume `output_index` via `_has_output_item` (:1315). The computer lane is a bare output-exists pre-filter (:2358–2362) before `_build_plan_for_resume_turn` — no approvals.
**Invariant:** a call with a persisted output never executes, rejects, or re-interrupts again; a rejected call emits exactly one rejection output per resume; an undecided call re-interrupts with the SAME persisted approval item (no duplicate approval churn); `UserError` from a needs-approval checker propagates while any other checker failure fails safe to needs-approval.
**Probe:** `tests/test_hitl_error_scenarios.py::test_rejected_shell_calls_emit_rejection_output` (:3456 pins one `shell_call_output` with the rejection message + `NextStepRunAgain`), `::test_rejected_shell_calls_with_existing_output_are_not_duplicated` (:3516), `::test_resume_skips_shell_calls_with_existing_output` (:2907 pins the output-exists skip), `tests/test_apply_patch_tool.py` (apply_patch rejection items).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "_collect_runs_by_approval rejection_builder output_exists_checker", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single generic collector with injected extractors/builders/checkers — it keeps four tool families in approval lockstep. Adapt the per-type adapter closures and rejection item shapes to your host's tool taxonomy. Omit the apply_patch per-operation approval short-circuit only if your tool has no per-operation approval predicate. Coverage caveat: Codebase Memory MCP not connected this pass; evidence is direct source+test reading at verified HEAD.
