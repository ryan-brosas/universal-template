<!-- capsule-v2 -->
# StorageFacade + relational duality — how do you give every subsystem one cached connection point to SQLite-or-Postgres while keeping destructive file resets safe?

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Multiple subsystems (secrets store, config store, conversation history) share one local DB — where should the mode switch, caching, and reset-invalidation live so a deleted DB file can't poison cached connections?

## Facade with explicit invalidation
**Path/Symbol:** `src/cuga/backend/storage/facade.py` (`get_storage` :13-17 module singleton; `_local_db_path` :24-42; `StorageFacade.get_relational_store` :58-65; `invalidate_relational_stores` :72-86), `relational/local.py` (`LocalRelationalStore` :6-66), `relational/prod.py` (`ProdRelationalStore` :20-72).
**Signature:** `get_storage() -> StorageFacade`; `facade.get_relational_store(db_name) -> RelationalStore`; `invalidate_relational_stores() -> None`; Protocol `RelationalStore`: `execute(sql, params)`, `fetchall`, `fetchone`, `commit()`, `close()`.
**Data Shape:** All three factories (`get_relational_store` / `get_embedding_store` / `get_policy_store_backend`) take the same `(mode, local_db_path, postgres_url)` triple via `get_storage_connection_params()`. Local store returns dict rows (sqlite3.Row → dict); prod converts asyncpg Records to dicts. Prod `execute` parses rowcount from asyncpg's command-status STRING ("UPDATE 3") by splitting and int-ing the last token.

### Decisive source
```python
# facade.py:24-42 — credential DB gets 0o600 on CREATE and AGAIN on existing files
# (touch sets mode only at create; chmod covers pre-existing), best-effort on
# filesystems that don't honor POSIX modes
p = _Path(DBS_DIR) / "cuga.db"
p.touch(mode=0o600, exist_ok=True)
p.chmod(0o600)

# facade.py:72-86 — after a destructive reset deletes cuga.db, cached stores must go:
for store in self._relational_stores.values():
    close_sync = getattr(store, "close_sync", None)   # sync close when supported
    if callable(close_sync):
        try: close_sync()
        except Exception: pass                        # never block the reset path
self._relational_stores.clear()                       # else lazy reopen on next access

# relational/local.py:19-21 — WAL is REQUIRED: three-file unit (see probe)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")

# relational/local.py:34-36 — EVERY op takes the asyncio lock AND hops threads;
# check_same_thread=False makes the single conn usable across that hop
async def execute(self, sql, params=()):
    async with self._lock:
        await asyncio.to_thread(self._execute_sync, sql, params)
```

**Flow:** first caller triggers module singleton → per-db_name memoized store creation → mode=="prod" demands postgres_url (loud ValueError) else SQLite at the 0o600 path. Reset flow elsewhere deletes the DB file then calls `invalidate_relational_stores()`; stores WITH `close_sync` close synchronously, pool-backed prod stores just drop for lazy reopen. `commit()` on prod is a no-op (asyncpg autocommits per statement); on local it's a real guarded commit.
**Invariant:** (1) WAL mode means the DB is a THREE-FILE unit (`cuga.db`, `-wal`, `-shm`) — deleting only the main file leaves sidecars describing pages the recreated file doesn't have → SQLITE_IOERR_SHORT_READ surfacing as an opaque "disk I/O error"; any destructive reset MUST remove all three (that's exactly what `reset_config_db` does). (2) The lock+to_thread pairing is what makes ONE sqlite connection safe across concurrent async callers — removing either half invites cross-thread misuse or interleaved writes. (3) `close_sync` exists because destructive-reset callers are synchronous; don't await inside it. (4) Never cache a relational store outside the facade — invalidation can't reach you.
**Probe:** `tests/unit/test_storage_facade.py::test_invalidate_relational_stores_closes_and_clears` (:10 asserts close called AND map emptied), `::test_invalidate_relational_stores_tolerates_stores_without_close_sync` (:25 PoolStore must not raise), `::test_local_store_close_sync_resets_connection` (:37 `_conn is None` after). WAL sidecar contract pinned by `tests/unit/test_config_db_reset_wal_sidecars.py::test_reset_config_db_removes_wal_sidecars` (:38 builds a REAL WAL db, orphans `-wal`/`-shm`, asserts all three removed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "StorageFacade get_relational_store invalidate_relational_stores LocalRelationalStore ProdRelationalStore", limit: 10 });
```

## Verdict
Adopt the facade singleton with per-name store caching + explicit invalidate-on-destructive-reset hook, the 0o600 touch-AND-chmod pattern for credential DBs, WAL+NORMAL pragmas, and the lock/to_thread wrapper. Adapt pool sizing (1..4) and the asyncpg rowcount-string parsing to your host. Omit the demo-oriented default DBS_DIR layout if your host has its own config root — but keep mode-prod-without-url as a loud startup error.
