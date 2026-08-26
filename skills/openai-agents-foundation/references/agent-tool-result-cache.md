<!-- capsule-v2 -->
# Agent-as-tool nested-run cache — where does a child agent's RunResult live between its tool-call start and the batch executor consuming it?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** How are nested agent-as-tool results stored, found across tool-call object instances, cleaned up, and preserved while approvals are pending?

## Identity-first cache with scope-qualified signature fallback
**Path/Symbol:** `src/agents/agent_tool_state.py:` module maps (:37–48), `record_agent_tool_run_result` (:145–156), `consume_agent_tool_run_result` (:208–230), `peek_agent_tool_run_result` (:233–252), weakref GC hook `_register_tool_call_ref` (:131–142), resume checkpoints (:19–31, :159–205).
**Signature:** `consume/peek/drop_agent_tool_run_result(tool_call, *, scope_id: str | None)`.
**Data Shape:** primary key `(scope_id, id(tool_call))`; fallback key `(scope_id, (call_id, name, arguments, type, id, status))` → set of scoped objects; values: `RunResult | RunResultStreaming | _AgentToolResumeCheckpoint(state, approval_identities)`.

### Decisive source
```python
scoped_object = (scope_id, id(tool_call))
run_result = _agent_tool_run_results_by_obj.pop(scoped_object, None)
if run_result is not None:
    _drop_agent_tool_run_result(scoped_object); return run_result
signature = _scoped_tool_call_signature(tool_call, scope_id=scope_id)
candidate_ids = _agent_tool_run_results_by_signature.get(signature)
if not candidate_ids: return None
if len(candidate_ids) != 1: return None            # ambiguity fails closed
candidate_id = next(iter(candidate_ids))
run_result = _agent_tool_run_results_by_obj.pop(candidate_id, None)
_drop_agent_tool_run_result(candidate_id); return run_result
```

**Flow:** nested runs record their result at tool-call identity → the executor peeks first (`_execute_single_tool_body` :2002) to detect in-flight nested approval interruptions, then consumes when building results (`_build_function_tool_results` :2244) → `_resolve_nested_tool_run_result` (:2225–2237) deliberately PEEKS while interruptions remain unresolved so replayed/re-created tool-call objects still find the state via the signature fallback, and only consumes once clean → a weakref callback deletes entries when the original tool-call object is garbage-collected → resume checkpoints keep the live nested RunState plus a frozenset of accepted approval identities (`tool_invocation_identity_and_scope`) and answer `agent_tool_resume_checkpoint_owns_approval` by membership.
**Invariant:** same call_id from two restored states must NOT cross-contaminate (scope ids partition); an ambiguous signature (≠1 candidate) returns None instead of guessing; cache lifetime is bounded by tool-call object lifetime (weakref), never by global state; unresolved nested approvals withhold the tool output item entirely (executor returns `run_item = None`).
**Probe:** `tests/test_agent_tool_state.py::test_agent_tool_run_result_supports_signature_fallback_across_instances` (:56), `::test_agent_tool_run_result_returns_none_for_ambiguous_signature_matches` (:69), `::test_agent_tool_run_result_keeps_same_call_isolated_by_scope` (:89), `::test_agent_tool_run_result_is_dropped_when_tool_call_is_collected` (:103).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "openai-agents-python", function_name: "consume_agent_tool_run_result", mode: "callers" }); // → _FunctionToolBatchExecutor.{execute,_build_function_tool_results,_resolve_nested_tool_run_result}
```

## Verdict
Adopt identity-primary + unique-signature-fallback caching, scope partitioning, fail-closed ambiguity, weakref-GC cleanup, and peek-vs-consume preservation for pending nested approvals. Adapt the checkpoint payload to your interruption type. Omit codex/thread-specific callers. Coverage: no_recorded_issue at gen 2026-08-24T14:05:06Z.
