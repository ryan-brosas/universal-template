<!-- capsule-v2 -->
# SQLite flow persistence — append-only snapshots, latest-row restore, and the cross-process file lock

**Source:** crewAI MIT `main@9e9a8577`; Codebase Memory `ext-crewAI`. **Question:** What write/restore discipline makes `@persist` safe under concurrent flows on one database — including the lock a porter will forget?

## Connected graph-selected seam
**Path/Symbol:** `lib/crewai/src/crewai/flow/persistence/sqlite.py` — `SQLiteFlowPersistence` (:24), `_save_state_sql` (:114), `load_state` (:178), `save_pending_feedback` (:205).
**Signature:** `save_state(flow_uuid: str, method_name: str, state_data: dict | BaseModel) -> None`; `load_state(flow_uuid) -> dict | None`; `_lock_name = f"sqlite:{os.path.realpath(self.db_path)}"` (:67).
**Data Shape:** `flow_states(id PK AUTOINCREMENT, flow_uuid, method_name, timestamp, state_json)` + index on flow_uuid; every save INSERTs a NEW row (append-only history, never UPDATE); restore = `ORDER BY id DESC LIMIT 1`.

### Decisive source
```python
# :73 init_db — WAL journal + named lock from REAL path (symlink-stable)
with (store_lock(self._lock_name),
      sqlite3.connect(self.db_path, timeout=30) as conn):
    conn.execute("PRAGMA journal_mode=WAL")
    ...

# :172 save_state — same double-guard; _save_state_sql is the no-lock inner core
with (store_lock(self._lock_name),
      sqlite3.connect(self.db_path, timeout=30) as conn):
    self._save_state_sql(conn, flow_uuid, method_name, state_dict)

# :188 load_state — deliberately NO store_lock; readers rely on WAL isolation
cursor = conn.execute("""
    SELECT state_json FROM flow_states
    WHERE flow_uuid = ? ORDER BY id DESC LIMIT 1""", (flow_uuid,))
...
return result if isinstance(result, dict) else None   # non-dict JSON -> None
```

**Flow:** model_validator runs `init_db()` at construction → each method completion appends a snapshot row keyed by flow uuid + method name → restore/fork reads the newest row only → pending-feedback save reuses `_save_state_sql` then upserts the UNIQUE-scoped marker in the SAME connection so state+marker are atomic. The lock is `crewai_core.lock_store.lock("sqlite:<realpath>")` — a NAMED CROSS-PROCESS lock, not a threading.Lock.
**Invariant:** Writers serialize on the realpath-named lock with 30s sqlite timeout; readers take NO lock because append-only writes under WAL never block them — porting this to "one connection reused" or dropping the named lock breaks multi-process crews/flows sharing one db file. `state_json` that isn't a dict deserializes as None (restore falls back silently). `@persist` fires through `PersistenceDecorator.persist_state` AFTER each method (:2931), offloaded via `asyncio.to_thread`.
**Probe:** `grep -c 'store_lock(self._lock_name)' lib/crewai/src/crewai/flow/persistence/sqlite.py` → `4`; `grep -c 'ORDER BY id DESC' lib/crewai/src/crewai/flow/persistence/sqlite.py` → `1`; `grep -c 'PRAGMA journal_mode=WAL' lib/crewai/src/crewai/flow/persistence/sqlite.py` → `1`.
**Direct test:** `tests/test_flow_persistence.py` (full suite green: fork/resume/cyclic-persist); `tests/test_flow_resumability_regression.py::test_hitl_resumption_skips_completed_listeners` uses SQLiteFlowPersistence against tmp_path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "SQLiteFlowPersistence save_state flow states", limit: 5 });
// → ext-crewAI...flow.persistence.sqlite.SQLiteFlowPersistence.save_state Method 157-176; ._save_state_sql Method 114-144
```

## Verdict
Adopt append-only-snapshot + latest-row-restore + named-realpath-lock trio verbatim for any durable workflow-state store. Adapt schema columns/table names. Omit provider factory registration details (`persistence/factory.py`) unless porting the plugin surface too.
