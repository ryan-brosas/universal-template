<!-- capsule-v2 -->
# Resume approval reconciliation — how does a resumed turn re-bind approvals, stale tool runs, and nested agent-as-tool state without re-executing or losing outputs?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** When `Runner.run` resumes a `RunState` interrupted on approvals, how are the persisted approval items validated against the re-processed response, and what happens to tool runs whose tool, arguments, or nested state changed between snapshot and resume?

## Snapshot → coerce → validate → reconcile ladder
**Path/Symbol:** `src/agents/run_internal/turn_resolution.py:` `resolve_interrupted_turn` (:1134 entry; early short-circuit :1160–1188), `_snapshot_function_run` (:1641–1657), `_coerce_approval_call` (:1739–1786), approval validation gate (:1788–1830), `_reject_nested_replacement` (:2090–2101), `_rebind_function_run` (:2103–2119), per-call reconciliation (:2121–2248), nested-approval sweep (:2249–2300), `_approved_tool_invocation_status` pre-validation (:2327–2336); `src/agents/run_internal/tool_planning.py:` `_select_function_tool_runs_for_resume` (:883–936).
**Signature:** `resolve_interrupted_turn(*, bindings, original_input, original_pre_step_items, new_response, processed_response, hooks, context_wrapper, run_config, server_manages_conversation=False, run_state=None, error_handlers=None, nest_handoff_history_fn=None) -> SingleStepResult`.
**Data Shape:** `stable_function_runs` are deep-copied tool calls paired with the live run's `function_tool`; `validated_function_approval_items` maps original→rebuilt `ToolApprovalItem`; reconciliation mutates `processed_response.functions/.handoffs` in place.

### Decisive source
```python
def _rebind_function_run(stale_run, current_run):
    if stale_run is None: return current_run
    cached_result = _cached_nested_result(stale_run)
    pending_result = _pending_nested_result(stale_run)
    if stale_run.function_tool is not current_run.function_tool:
        stale_owner = getattr(stale_run.function_tool, "_agent_instance", None)
        current_owner = getattr(current_run.function_tool, "_agent_instance", None)
        if pending_result is not None and (stale_owner is None or stale_owner is not current_owner):
            _reject_nested_replacement(stale_run)   # raises ModelBehaviorError
        if cached_result is not None and pending_result is None:
            pending_nested_drops.append(stale_run.tool_call)
    if pending_result is not None and current_run.tool_call is not stale_run.tool_call:
        pending_nested_transfers.append((current_run.tool_call, pending_result))
        pending_nested_drops.append(stale_run.tool_call)
    return current_run
```

**Flow:** on resume, every queued function run is deep-copy snapshotted (`_snapshot_function_run`) while the live call object is kept as the mutation source and nested results are *peeked* (not consumed) → each persisted `ToolApprovalItem` is coerced back into a `ResponseFunctionToolCall` (`_coerce_approval_call`: type/name/call_id/arguments must be strings; status/namespace/caller/id restored; persisted lookup key re-attaches routing identity) → validation is fail-closed: non-function raw items, missing fields, or a persisted lookup key that no longer matches the queued call's lookup-key↔call-id sets mark the approval malformed and the whole turn re-interrupts with the pending approvals (no partial execution) → per reconciled call_id the ladder is: current function run exists → rebind (nested-state transfer/drop/reject rules above); handoff exists + approved → reject nested replacement then take the handoff; tool missing + approved → not-found lane (raise unless `tool_not_found_behavior == "return_error_to_model"`, cached nested result reused as a state call); stale-only run → keep the stale run; approval status None → re-interrupt, False → rejection output item → after the ladder, nested (non-matching-agent) approvals are swept: agent-tool checkpoint ownership suppresses re-interruption, nested context status None re-interrupts → before any user code, every selectable run and handoff is re-validated via `context_wrapper._approved_tool_invocation_status` so a changed invocation under an approved call ID fails BEFORE tool-inventory callbacks (pinned by `test_changed_nested_parent_fails_before_tool_inventory_callbacks`) → `_select_function_tool_runs_for_resume` then filters by output-exists → approval status (None triggers a `needs_approval` re-check then a second status read) → False records a rejection → True or not-requiring selects → otherwise re-interrupts.
**Invariant:** resume never executes a call whose identity, arguments, or owning tool changed since the interruption (fail loud via `ModelBehaviorError`); malformed approvals fail the whole turn closed rather than partially executing; nested agent-as-tool pending results transfer to the rebound call exactly once and cached-but-not-pending results drop; legacy schema <1.7 snapshots may match approvals by agent *name* (duplicate-name deserialization) while 1.7+ requires object identity.
**Probe:** `tests/test_run_impl_resume_paths.py::test_resumed_approval_does_not_duplicate_session_items` (:421 one call+output after resume), `::test_resolve_interrupted_turn_only_uses_name_fallback_for_legacy_approval_agents` (:468 parametrized 1.6 vs 1.7), `tests/test_hitl_error_scenarios.py::test_changed_nested_parent_fails_before_tool_inventory_callbacks` (:379), `::test_nested_agent_tool_resumes_after_rejection` (:317).
