<!-- capsule-v2 -->
# DBOS legacy-workflow replay compat — recorded step sequences are sacred

## Source / Question
`pydantic_ai_slim/pydantic_ai/durable_exec/dbos/_durability.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** You migrated a wrapper-class API to a capability, but in-flight durable workflows recorded their step sequence under the OLD shape — how do you keep those recordings recoverable while new runs take the new path? A porter will route old recordings through the new step layout and fail recovery with unexpected-step errors.

## Path / Symbol
`_durability.py` — `DBOSDurability` (:36–64; note `_unsupported_runtime_toolset_kinds = {'mcp','dynamic'}` — DBOS has NO function-toolset restriction), `_init_legacy_context_vars` pair (:125–134), fresh-ContextVars-on-bind (:139–143), steps trio + handler step (:147–204), opt-in legacy workflow registration (:206–241), `in_durable_context = DBOS.workflow_id is not None and DBOS.step_id is None` (:243–245), enqueue guard only inside workflows (:247–250), legacy branch of `_dispatch_event_stream_event` (:252–261), legacy-history stream unwrap (:321–333).

## Signature
```python
self._in_legacy_workflow: ContextVar[bool] = ContextVar('_in_legacy_workflow', default=False)
self._legacy_run_event_stream_handler: ContextVar[EventStreamHandler | None] = ContextVar(...)

@DBOS.workflow(name=f'{self.name}.run')
async def legacy_run_workflow(*args, **kwargs):
    handler = kwargs.pop('event_stream_handler', None)      # wrapper-era input
    legacy_token = self._in_legacy_workflow.set(True)
    token = self._legacy_run_event_stream_handler.set(handler) if handler is not None else None
    try:
        return await agent.run(*args, **kwargs)
    finally:
        ...reset both...
```

## Data Shape
Wrapper-era recordings contain NO `__event_stream_handler` steps (the old wrapper called the handler directly at workflow level): model events were delivered live inside `__model.request_stream`, graph events by a direct workflow-level call consuming no step. Routing them through the new per-event step would insert step ids the recording doesn't have → `DBOSUnexpectedStepError` on recovery.

### Decisive source — mirror the old delivery, don't upgrade it (:252–261)
```python
if self._in_legacy_workflow.get():
    # Wrapper-era recordings contain no `__event_stream_handler` steps ..., so a legacy run must do the same
    # to keep the recorded step sequence replayable. The handler runs at workflow level here, not inside
    # a step, so the enqueue guard doesn't apply — matching how the wrapper delivered it.
    await handler(ctx, self._single_event_stream(event))
    return
```
Two more port-critical details: (1) `_bind_to_agent` RE-INITIALIZES the ContextVars because `for_agent` shallow-copies capability instances — one instance on several agents would otherwise leak per-run legacy state across agents (:139–143); (2) a legacy-history bare-response stream result is re-wrapped with `CompletedStreamedResponse(result, replay_events=True)` so old recordings stream (:325–332). Also: run-scoped MCP tool-defs cache — cache lives on the RUN, never process-shared, else run 2 inherits warm state and records ZERO get_tools steps → different recording than cold run → unreplayable (pinned by test_dbos.py :2250–2272, #4331/#5875).

**Flow:** opt-in flag registers `{name}.run`/`{name}.run_sync` workflows that stash handler + legacy flag in ContextVars → during such runs event dispatch mirrors wrapper-era delivery exactly → new-capability runs take the checkpointed per-event step.

**Invariant:** Never change what an in-flight recording's step sequence looks like; version migrations add NEW paths selected by run-time flags, keeping old byte-for-byte delivery semantics for recorded runs. Per-run mutable state must be instantiated per binding, never shared via shallow copies.

**Probe:** `tests/test_dbos.py::test_dbos_durability_registers_legacy_workflows_opt_in` (:2380 — flags + registered names + a live legacy run), MCP replay-determinism test (:2250 docstring, asserts identical step lists across back-to-back cold runs).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'DBOSDurability legacy_run_workflow _in_legacy_workflow'
```

## Verdict
**Adopt** the ContextVar-flagged dual-path migration pattern and run-scoped caching rule. **Adapt** nouns/steps to your engine. **Omit** DBOS-specific config plumbing.
