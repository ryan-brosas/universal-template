<!-- capsule-v2 -->
# TemporalAgent workflow surface — entry-point guards and the in-workflow override sandwich

## Source / Question
`pydantic_ai_slim/pydantic_ai/durable_exec/temporal/_agent.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** One Agent class must run both non-durable (outside Temporal) and durable (inside a replaying workflow), but streaming APIs, sync calls, contextual overrides, and realtime sessions are all illegal or need re-routing inside a workflow — how do you shape ONE class so each entry point fails loudly or delegates correctly? A porter will let `run_stream` execute inside a workflow (non-deterministic events lost on replay) or allow a mid-workflow `override(model=...)` that breaks determinism.

## Path / Symbol
`_agent.py` — `_merge_activity_config` (:78–88), `TemporalAgent.__init__` name/config normalization (:180–203), `event_stream_handler` property + `_call_event_stream_handler_activity` (:298–324), `_temporal_overrides` context manager (:335–371), `run_sync` guard (:652–656), `run_stream` guard (:801–806), `run_stream_events` guard (:975–978), `iter` in-workflow branch (:1172–1193), `_resolve_realtime_session`/`_open_realtime_session` guards (:1242–1247, :1292–1296), `override` guards (:1355–1371).

## Signature
```python
class TemporalAgent(WrapperAgent[AgentDepsT, OutputDataT]):
    def __init__(self, wrapped, *, name=None, models=None, provider_factory=None,
                 event_stream_handler=None, activity_config=None,
                 model_activity_config=None, toolset_activity_config=None,
                 tool_activity_config=None, run_context_type=..., temporalize_toolset_func=...)
    def _temporal_overrides(self, *, model=None, additional_toolsets=None, force=False) -> Generator[None]
    # every public entry point starts with:
    reject_cancellation_token(cancellation_token, engine='Temporal')
    if workflow.in_workflow(): raise UserError(...)
```

## Data Shape
`_temporal_overrides_active: ContextVar[bool]` distinguishes "iter() called by `run()` under our own overrides" (allowed) from "user called iter() directly in a workflow" (UserError). Activity config layers: base `activity_config` ← `model_activity_config` / `toolset_activity_config[id]` ← `tool_activity_config[id][tool]`; `False` disables the activity for an IO-free tool (which must then be `async` — sync tools run in threads, non-deterministic outside activities).

### Decisive source — the override sandwich (:355–364)
```python
merged_toolsets = [*self._toolsets, *(additional_toolsets or ())]
with (
    super().override(model=self._temporal_model, toolsets=merged_toolsets, tools=[]),
    self._temporal_model.using_model(model),
    _utils.disable_threads(),                                # threads are non-deterministic
    _agent_graph.set_agent_graph_sleep(workflow.sleep),      # delays survive replay
):
```
Every leg is load-bearing: tools=[] because constructor-time toolsets were ALREADY temporalized into `self._toolsets`; `workflow.sleep` replaces `asyncio.sleep` so graph delays become recorded commands; thread-executor disablement forces everything through activities.

**Flow:** `run()` inside workflow → `_temporal_overrides` sets ContextVar + swaps model/toolsets/sleep → graph's `iter()` sees `_temporal_overrides_active.get()` True → allowed; user-direct `iter()`/`run_stream()`/`run_sync()` see no active override → UserError naming `agent.run()` as the replacement; PydanticSerializationError escaping the body is re-raised as `serialization_user_error`.

**Invariant:** Inside a workflow NOTHING non-deterministic may run on the workflow task: streams route through `event_stream_handler` activities (per-event `execute_activity`, summary `'handle event: {kind}'`), sync/blocking entry points and realtime sessions raise, model/toolset/tools overrides raise ("must be set at agent creation time"), and cancellation tokens are rejected everywhere (`reject_cancellation_token`) because Temporal has its own cancellation machinery.

**Probe:** `tests/test_temporal.py::test_temporal_agent_run_stream_in_workflow` (:2778 — snapshot of the UserError), `test_temporal_agent_iter_in_workflow` (:2838), `test_temporal_agent_run_sync_in_workflow` (:2674 snapshot), `test_anyio_scope_cancel_of_activity_await_does_not_wedge` (:528).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'TemporalAgent _temporal_overrides run_stream in_workflow UserError'
```

## Verdict
**Adopt** the entry-point guard ladder (reject token → in_workflow check → ContextVar-gated delegation) and the four-leg override sandwich. **Adapt** error wording and which entry points your engine supports. **Omit** the deprecated wrapper-era migration shims if you start from capabilities.
