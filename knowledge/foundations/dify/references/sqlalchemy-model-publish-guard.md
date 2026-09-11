<!-- capsule-v2 -->
# sqlalchemy-model-publish-guard — Why can't you just put any object on the queue?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** What class of object must never cross the producer/consumer thread boundary, and how is that enforced?

## Recursive publish-time guard raising on ORM instances
**Path/Symbol:** `api/core/app/apps/base_app_queue_manager.py:AppQueueManager.publish` (:152-160) + `_check_for_sqlalchemy_models` (:235-249).
**Signature:** `publish(event: AppQueueEvent, pub_from: PublishFrom)`; `_check_for_sqlalchemy_models(data: Any)`.
**Data Shape:** Walks `event.model_dump()` recursively through dicts and lists; raises TypeError on any node that is a SQLAlchemy `DeclarativeMeta` or carries `_sa_instance_state`.

### Decisive source
```python
def publish(self, event: AppQueueEvent, pub_from: PublishFrom) -> None:
    self._check_for_sqlalchemy_models(event.model_dump())
    self._publish(event, pub_from)

def _check_for_sqlalchemy_models(self, data: Any):
    match data:
        case dict():
            for value in data.values():
                self._check_for_sqlalchemy_models(value)
        case list():
            for item in data:
                self._check_for_sqlalchemy_models(item)
        case _:
            if isinstance(data, DeclarativeMeta) or hasattr(data, "_sa_instance_state"):
                raise TypeError(
                    "Critical Error: Passing SQLAlchemy Model instances that"
                    " cause thread safety issues is not allowed."
                )
```

**Flow:** every event → model_dump (pydantic serializes scalars/containers) → recursive scan → clean payload reaches the internal queue; ORM-tainted payloads die at the PUBLISH site with a loud error rather than failing later in the consumer thread where the session that produced them may already be closed.
**Invariant:** The guard runs BEFORE enqueueing (fail-fast at the offender's call site), not at consume time; detection is dual (`isinstance(DeclarativeMeta)` OR duck-type `_sa_instance_state`) so custom bases are caught too. Porters who drop this get non-deterministic `DetachedInstanceError`s in a different thread from where the bug lives.
**Probe:** `grep -c '_sa_instance_state' core/app/apps/base_app_queue_manager.py` → 1; direct test `tests/unit_tests/core/app/apps/test_base_app_queue_manager.py::test_check_for_sqlalchemy_models_raises`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "AppQueueManager _check_for_sqlalchemy_models DeclarativeMeta thread safety TypeError", limit: 10 });
```

## Verdict
Adopt the fail-fast-at-publish boundary guard for ANY thread/process handoff of event payloads. Adapt the forbidden-type list to your ORM (the duck-typed `_sa_instance_state` check is the portable half). Omit nothing.
