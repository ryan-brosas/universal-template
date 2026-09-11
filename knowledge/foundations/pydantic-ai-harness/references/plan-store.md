<!-- capsule-v2 -->
# PlanStore — six-method async CRUD with an event-emission asymmetry that must be loud

**Source:** pydantic-ai-harness (MIT) `main@c79fabc58fd3bd587dcc27f9e7d9de179d748cf0`; Codebase Memory `pydantic-ai-harness`. **Question:** how does a planning capability persist an ordered list of steps across in-memory / SQLite / Postgres backends, and what trap does a porter get wrong around events and duplicate ids?

## PlanStore protocol
**Path/Symbol:** `pydantic_ai_harness/planning/_store.py` — `PlanStore` (runtime_checkable Protocol), `InMemoryPlanStore`, `SqlitePlanStore`; `_postgres.py` (`PostgresPlanStore`); `_events.py` (`PlanEvent`, `PlanEventEmitter`); `_types.py` (`PlanItem`, `TaskStatus`).
**Signature:** `get_items / set_items / get_item / add_item / update_item / remove_item` (all async).
**Data Shape:** ordered list of `PlanItem` steps. Backends: InMemory, Sqlite, Postgres — all emitting identical events.

### Decisive source
```python
# set_items is BULK REPLACEMENT and does NOT emit PlanEvents -- so the
# write_plan tool, which calls it, is event-silent while granular tools
# (add_task, update_task_status, ...) emit. Applications rendering off events
# should also read after a run, or steer the model toward the granular tools.
# Duplicate ids raise ValueError (every reader resolves first-match, so a
# duplicate makes updates land randomly; SQL stores enforce via primary key).
# Table names validated against [A-Za-z_][A-Za-z0-9_]{0,62} before SQL interpolation.
```

**Flow:** capability tools call the protocol; granular mutations emit events; `set_items` is the silent bulk path. SQL backends enforce uniqueness via primary key; in-memory checks.
**Invariant:** event-emission asymmetry is a documented, deliberate contract — a porter must not "fix" it by making `set_items` emit, nor silently rely on events after a bulk write. Ids unique per store.
**Probe:** `tests/planning/test_stores.py`, `test_planning.py`, `test_postgres.py`, `test_redis.py` pin CRUD, event emission, duplicate rejection, and backend parity.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "PlanStore set_items add_item PlanEventEmitter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the six-method protocol with the loud event asymmetry and duplicate-id rejection; adapt the backend storage; omit host-specific event consumers.
