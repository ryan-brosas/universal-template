<!-- capsule-v2 -->
# Supervisor delegation — ambient execution context via stack-walking and frame-resolved variable passing

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** A supervisor generates Python that calls `delegate_to_agent(...)` mid-script, but the delegation tool was built at prepare time while runtime state (supervisor state, variable manager) only exists inside the executing block. How do tools reach per-execution runtime state without storing it on the long-lived graph adapter — and how do you pass script variables the model referenced by NAME?

## The delegation contract
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_supervisor/execution_context.py` (`SUPERVISOR_EXEC_KEY="__supervisor_exec__"` :18, `SupervisorExecutionContext` :20-23, `resolve_supervisor_execution_context` :26-38); `cuga_supervisor/delegation.py` (`resolve_names_from_caller_frame` :30-63, `create_agent_delegation_func` :89-190).
**Signature:** `resolve_supervisor_execution_context() -> SupervisorExecutionContext | None`; `delegate_to_agent(task: str, variables: Optional[List[str]] = None) -> Any`.
**Data Shape:** runtime state injected into executor locals under `__supervisor_exec__` for the duration of each execute call; resolved variables are a name→value dict.

### Decisive source
```python
# execution_context.py:31-37 — ambient context by walking the CALL STACK,
# not module globals or a singleton
current = frame.f_back if frame is not None else None
while current is not None:
    for scope in (current.f_locals, current.f_globals):
        ctx = scope.get(SUPERVISOR_EXEC_KEY)
        if isinstance(ctx, SupervisorExecutionContext):
            return ctx
    current = current.f_back

# delegation.py:33-48 — resolve from the SCRIPT frame, not the wrapper frame
# Walk to the frame holding ``SUPERVISOR_EXEC_KEY`` (``_async_main``), not the
# immediate ``delegate_to_agent`` wrapper. Fill names missing from that frame
# from the supervisor VM (prior-turn values are not locals yet).
while current is not None:
    if _frame_has_supervisor_exec(current): exec_frame = current; break
    current = current.f_back
...
if any(name not in resolved for name in variable_names):
    vm_vars = _variables_from_supervisor_vm()   # fallback: prior-turn values
```

**Flow:** prepare-time builds one `delegate_to_agent` per agent via `create_agent_delegation_func(adapter, agent_name, agent_or_config, agent_card)`. At call time it dispatches on target type: **internal CugaAgent** → resolve variables (explicit list resolved from the caller's script frame, else ALL supervisor VM variables auto-passed), invoke with a stable thread id, bridge returned sub-agent variables into the supervisor VM via `VariableBridge.bridge(...)` with a "from {agent}" description prefix; **external dict with a2a config** → SDK path when an agent_card + http transport exist, else legacy `A2AProtocol` connect/delegate/disconnect (variables forwarded only when `settings.supervisor.pass_variables_a2a` is on); every branch ends in `_record_delegation` which resolves the ambient context and calls `adapter.record_delegation(state, ...)` — silently no-op when no execution is active.
**Invariant:** runtime state lives ONLY in the executing frame (injected per execute call, never on the adapter) so concurrent runs can't cross-contaminate; name resolution prefers the generated script frame because mid-script locals aren't in the VM yet, with VM fallback for prior-turn values; an EMPTY explicit variables list means "no variables" (not auto-pass). Errors for unknown agent types return a string answer through the same recording path — never raise out of generated code.

**Probe:** direct tests `cuga_supervisor/tests/test_execution_context.py::test_resolve_supervisor_execution_context_from_locals`; `tests/test_delegation_recording.py::test_delegation_forwards_mid_script_explicit_variables` (:227), `::test_delegation_auto_passes_supervisor_variables_when_omitted` (:197), `::test_delegation_empty_variables_list_does_not_auto_pass` (:246), `::test_record_delegation_updates_state_fields` (:90), `::test_legacy_a2a_does_not_send_variables_when_setting_off` (:339).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "resolve_names_from_caller_frame SUPERVISOR_EXEC_KEY create_agent_delegation_func VariableBridge", limit: 10 });
```

## Verdict
Adopt ambient-per-execution context via stack-walking (state scoped to the executing frame beats adapter-stored mutable state for concurrency), script-frame-first variable resolution with VM fallback, and result bridging with provenance descriptions. Adapt the exec-key name, thread-id scheme, and the pass-variables-over-A2A gate to your host. Omit the legacy non-SDK A2A transport once your clients speak the SDK protocol.
