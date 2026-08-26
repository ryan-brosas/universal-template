<!-- capsule-v2 -->
# Partial idempotency index — how is key uniqueness race-safe for new tasks yet blind to terminal rows recovery must find?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you enforce idempotency-key uniqueness at the DB for concurrent creates while letting the application-layer lookup still see terminal rows for crash-recovery replays?

## Unique only where it must be: ACTIVE rows
**Path/Symbol:** `packages/python/awaithumans/server/db/models/task.py` `_ACTIVE_IDEMPOTENCY_WHERE` + `Task.__table_args__` Index `ix_tasks_active_idempotency_key` (:15–35, :161–169); partner lookup `task_service._find_task_by_idempotency_key`.
**Signature:** `Index("ix_tasks_active_idempotency_key", "idempotency_key", unique=True, sqlite_where=text(...), postgresql_where=text(...))`.
**Data Shape:** WHERE clause = `status NOT IN ('CANCELLED','COMPLETED','TIMED_OUT',…)` — enum **NAMEs**, built by joining `s.name` over `TERMINAL_STATUSES_SET`, because SQLAlchemy stores Enum columns by name (uppercase), not `.value`.

### Decisive source
```python
_TERMINAL_STATUS_VALUES = (
    "(" + ", ".join(f"'{s.name}'" for s in sorted(TERMINAL_STATUSES_SET, key=lambda s: s.name)) + ")"
)
_ACTIVE_IDEMPOTENCY_WHERE = f"status NOT IN {_TERMINAL_STATUS_VALUES}"

class Task(SQLModel, table=True):
    __table_args__ = (
        Index("ix_tasks_active_idempotency_key", "idempotency_key", unique=True,
              sqlite_where=text(_ACTIVE_IDEMPOTENCY_WHERE),
              postgresql_where=text(_ACTIVE_IDEMPOTENCY_WHERE)),
    )
```

**Flow:** create path first runs the app-layer lookup, which returns ANY row carrying the key — terminal included — so a crashed agent re-invoking `await_human()` receives the stored response instead of duplicating work; only genuinely NEW keys reach INSERT, and there the partial unique index makes a concurrent duplicate lose loudly (IntegrityError) instead of racing two active tasks into existence.
**Invariant:** the index's WHERE must match the storage representation of the status column (enum NAME), or the filter silently matches nothing and uniqueness quietly disappears — hence deriving names from `TERMINAL_STATUSES_SET` rather than hand-copying literals; uniqueness is scoped to ACTIVE rows BY DESIGN, not a bug to "fix."
**Probe:** `packages/python/tests/tasks/test_task_metadata.py` :72–100 (replay returns the original task + metadata) and `tests/tasks/test_idempotency_after_terminal.py` (per-terminal-state recovery branches). Coverage caveat: no direct IntegrityError race test exists for tasks at this pin; the analogous unique-constraint fire is proven for service keys in `tests/embed/test_service_key_model.py` :42–68.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "_find_task_by_idempotency_key partial unique index active", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-layer split: unscoped application lookup for replay/recovery + partial UNIQUE index (active-only) for INSERT-race safety, with the predicate derived from the shared terminal-status constant. Adapt the dialect kwargs to your engine (both `sqlite_where` and `postgresql_where` shown; Postgres needs `CREATE UNIQUE INDEX … WHERE`). Omit nothing — dropping either layer breaks the other's guarantee.
