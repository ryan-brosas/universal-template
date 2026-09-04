<!-- capsule-v2 -->
# SQLite flow-state append-only ledger — why is every method completion an INSERT, and what does the lock name have to do with multi-process safety?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What must a flow persistence backend guarantee so resume picks up the latest snapshot across processes?

## WAL + realpath-named distributed lock + latest-row read
**Path/Symbol:** `lib/crewai/src/crewai/flow/persistence/sqlite.py` (`SQLiteFlowPersistence._setup` :64–69, `init_db` :71–112, `save_state` :157–176, `load_state` :178–198, `save_pending_feedback` :205–244, `clear_pending_feedback` :280–295).
**Signature:** `save_state(self, flow_uuid: str, method_name: str, state_data: dict[str, Any] | BaseModel) -> None`; `load_state(self, flow_uuid: str) -> dict[str, Any] | None`.
**Data Shape:** `flow_states(flow_uuid, method_name, timestamp, state_json)` append-only; separate `pending_feedback(flow_uuid UNIQUE, context_json, state_json, created_at)`.

### Decisive source
```python
self._lock_name = f"sqlite:{os.path.realpath(self.db_path)}"
...
with (
    store_lock(self._lock_name),
    sqlite3.connect(self.db_path, timeout=30) as conn,
):
    conn.execute("PRAGMA journal_mode=WAL")
```
```python
SELECT state_json
FROM flow_states
WHERE flow_uuid = ?
ORDER BY id DESC
LIMIT 1
```

**Flow:** validator computes the lock name from the REALPATH of the db (symlink-aliased paths still contend on one lock) → every write takes the process-wide `store_lock("sqlite:<realpath>")` (Redis-backed when `REDIS_URL`+redis present, else portalocker file lock in tmp), opens WAL-mode SQLite with 30s busy timeout → INSERT full state row per completion → reads take NO lock and return newest row by autoincrement id; non-dict JSON ⇒ None.
**Invariant:** Append-only rows are the version history — `ORDER BY id DESC LIMIT 1` is the "latest wins" rule, so backends MUST monotonicize their row ids. `pending_feedback.flow_uuid` is UNIQUE with `INSERT OR REPLACE`: at most one pause per flow. The pending-feedback save writes BOTH the normal state row AND the marker in ONE lock scope. Reads are deliberately lock-free (WAL readers never block).
**Probe:** `.venv/bin/python -m pytest lib/crewai/tests/test_flow_persistence.py -q` (expect 15 passed incl. restoration + multi-method ordering); anchor check: `grep -c "store_lock(self._lock_name)" lib/crewai/src/crewai/flow/persistence/sqlite.py` → 4.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "SQLiteFlowPersistence save_state pending_feedback store_lock WAL", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt realpath-derived lock names, WAL + insert-per-completion + newest-row read as a unit; adapt to Postgres by replacing the lock with advisory locks; omit the pending-feedback table only if you never pause flows. Direct tests executed green at pin.
