<!-- capsule-v2 -->
# TemporalRunContext guarded rehydration — omitted fields raise, never default

## Source / Question
`pydantic_ai_slim/pydantic_ai/durable_exec/temporal/_run_context.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A run context crosses a durable boundary as untyped JSON — sets arrive as lists, objects as dicts, and fields a custom serializer forgot to carry would silently read as their dataclass defaults (indistinguishable from real run state). How do you rehydrate so activity-side code either gets the real thing or a LOUD error? A porter will `RunContext(**payload)` and let `instrumentation_version=0` / `prompt=None` pass for truth.

## Path / Symbol
`_run_context.py` — `_REHYDRATORS` table (:30–39), `_NONE_UNLESS_ATTACHED` (:49), `_DEFAULTED_UNLESS_CARRIED` (:56), `_GUARDED_FIELDS` computation (:61), `TemporalRunContext.__init__` (`__dict__` swap + field-table rewrite :73–86), `__getattribute__` guard (:88–94), snapshot property trio (`available_tool_names`/`available_capability_ids`/`_deferred_capability_ids` :96–138), `serialize_run_context` (:140–179), module-level `deserialize_run_context` attaching agent + EnqueueGuard (:187–213).

## Signature
```python
_GUARDED_FIELDS = frozenset(RunContext.__dataclass_fields__) - {'deps', *_NONE_UNLESS_ATTACHED}
class TemporalRunContext(RunContext[AgentDepsT]):
    def __init__(self, deps, **kwargs):
        self.__dict__ = {**kwargs, 'deps': deps}          # bypass dataclass __init__
        ...setdefault None/defaulted...; ...rehydrate via TypeAdapter...
        setattr(self, '__dataclass_fields__', {n: f for n, f in RunContext.__dataclass_fields__.items() if n in self.__dict__})
    def __getattribute__(self, name):                      # un-carried guarded field => UserError
        if name in _GUARDED_FIELDS and name not in object.__getattribute__(self, '__dataclass_fields__'):
            raise UserError(f'{name!r} is not available on {self.__class__.__name__!r} inside a Temporal activity. ...')
```

## Data Shape
Four field classes: (1) **rehydrated** — wire dict/list → typed via TypeAdapter table (`usage`→RunUsage, `usage_limits`→UsageLimits, five id/name sets list→set[str], `_anchored_evidence` dict→AnchoredEvidence); (2) **None-unless-attached** — live objects reattached post-deserialize (`agent`, `root_capability`) or contractually None (`pending_messages`→EnqueueGuard, `tool_manager`, `realtime_session`); (3) **defaulted-unless-carried** — only `_anchored_evidence()` empty value where "empty" IS the truthful answer; (4) **guarded** — everything else: reading raises with instructions to extend `serialize_run_context`. Deliberately EXCLUDED from serialization: `messages`/`prompt` (would ride in every payload vs Temporal's 2 MB limit), `model`/`tracer`/`capabilities` (live objects — snapshots of derived ids/names travel instead).

### Decisive source — dispatch-time snapshots keep `is_tool_available` answering (:162–178)
```python
'_anchored_evidence': ctx._anchored_evidence,
'available_tool_names': ctx.available_tool_names,        # resolved at dispatch: includes always-visible tools
'available_capability_ids': ctx.available_capability_ids, # plain-string ids while registry objects can't travel
'_deferred_capability_ids': ctx._deferred_capability_ids,
```
Each property override falls back to the base (registry-reading) behavior when a legacy subclass didn't carry the snapshot — backward compat without silent wrong answers.

**Flow:** workflow side `serialize_run_context(ctx)` → JSON payload per event/activity → activity side `deserialize_run_context(...)` → subclass init rehydrates types + installs `EnqueueGuard` on `pending_messages` (a durable unit's result replays WITHOUT re-running, so an enqueue there would be dropped) → attaches live `agent`/`root_capability` so capability chains (e.g. ProcessEventStream) fire against real streams.

**Invariant:** A field that didn't cross the boundary must NEVER be readable as its default; "empty" defaults are allowed only where emptiness is semantically true; every set that tool-availability logic reads must be snapshotted at DISPATCH time, not recomputed from unreachable registries.

**Probe:** `tests/test_temporal.py::test_temporal_run_context_preserves_run_id` (:4320 round-trip family :4330–4415), guarded-field UserError snapshots (:4617 `'model_settings' is not available on 'TemporalRunContext'...`, :4830 `'prompt' is not available on...`), legacy-subclass guard sweep (:4751); enqueue-guard parity pinned by `tests/test_prefect.py::test_prefect_durability_event_stream_handler_rejects_enqueue` (:3005 — same EnqueueGuard message on both model-event and graph-event paths).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'TemporalRunContext _GUARDED_FIELDS serialize_run_context EnqueueGuard'
```

## Verdict
**Adopt** the four-class field taxonomy + `__getattribute__` loud-guard + dispatch-time availability snapshots. This is THE pattern for shipping a context object across any serialize/replay boundary. **Adapt** the field list to your context type. **Omit** nothing.
