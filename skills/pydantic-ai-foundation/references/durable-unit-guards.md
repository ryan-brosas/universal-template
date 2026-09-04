<!-- capsule-v2 -->
# Durable unit guards — enqueue and cancel inside a replayed unit would be silently dropped, so they raise

## Source / Question
`pydantic_ai_slim/pydantic_ai/durable_exec/_toolset.py` + `_base.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** User code inside a durable unit (tool call, hook, event handler) has its recorded result replayed on recovery/cache-hit WITHOUT re-running — so `ctx.enqueue()` or `ctx.cancel()` there would fire once and never again. How do you make those calls fail loudly instead of silently dropping? A porter will leave the live queue/controller reachable inside the unit.

## Path / Symbol
`_toolset.py` — `EnqueueGuard` (:194–204), `enqueue_not_supported_message` (:207–217), `CancelGuard` (:220–231), `cancel_not_supported_message` (:234–243), `guard_run_context` (:251–263); `_base.py` — `_durable_run_context_scope` (:309–319), `_durable_model_scope` (:321–336).

## Signature
```python
class EnqueueGuard(list[PendingMessage]):
    def append(self, pending: PendingMessage) -> None: raise UserError(self._message)
class CancelGuard(RunCancellation):
    def cancel(self) -> None: raise UserError(self._guard_message)
def guard_run_context(ctx, *, unit_noun: str, container_noun: str) -> RunContext
```

## Data Shape
Guards are type-compatible stand-ins: `EnqueueGuard` subclasses `list[PendingMessage]` (so any code reading/iterating `ctx.pending_messages` works; only mutation raises), `CancelGuard` subclasses `RunCancellation`. Messages are worded per engine via nouns: `'step'`/`'workflow'` (DBOS), `'activity'`/`'workflow'` (Temporal), `'task'`/`'flow'` (Prefect).

### Decisive source — both halves guarded at one chokepoint (_base.py :309–319)
```python
@contextmanager
def _durable_run_context_scope(self, ctx):
    """Both the yielded context AND get_current_run_context() are guarded, so user code can't
    enqueue whether it reads its argument or the ambient getter."""
    guarded = self._durable_run_context(ctx)
    with set_current_run_context(guarded):
        yield guarded
```
`_durable_model_scope` pairs guard+model-rebuild: every model unit needs both halves, "a unit can't get its model without the guard" — instead of each engine remembering per unit. Temporal is the exception: it reconstructs context across the activity boundary in `deserialize_run_context`, where the same enqueue guard is installed structurally (`CancelGuard` unneeded there because the live controller never serializes).

**Flow:** engine enters durable unit → `replace(ctx, pending_messages=EnqueueGuard(...), _cancellation=CancelGuard(...))` → ambient ContextVar set to the guarded copy → user code's enqueue/cancel raises with replay-explaining message → container-level code keeps the real queue/controller.

**Invariant:** The rationale is determinism, not capability: a replayed unit must not re-execute side effects, so side-effectful controls are refused AT the unit boundary with an explanation naming WHERE to do it instead ("Enqueue messages from workflow-level code instead").

**Probe:** `tests/test_dbos.py` :2727/:2769/:2815 and `tests/test_prefect.py` :3260/:3319 pin the byte-exact guard messages through real workflows/flows; `tests/test_temporal.py` :4519 pins `pending_messages` as an intentionally-unserialized field "replaced by an EnqueueGuard".

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'EnqueueGuard CancelGuard guard_run_context set_current_run_context'
```

## Verdict
**Adopt** type-compatible guard stand-ins, the argument-or-ambient double chokepoint, guard-paired-with-model scope, and noun-parameterized messages. **Adapt** your context-copy mechanism (`dataclasses.replace` here). **Omit** Temporal's serializer-side variant if you have no activity boundary.
