<!-- capsule-v2 -->
# SQLite history storage — schema-migrating, thread-locked memory history

**Source:** mem0 MIT `<branch>@<commit>`; Codebase Memory `mem0`. **Question:** how does a memory system persist add/update/delete history and last messages in SQLite with migration + thread safety?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/storage.py` (347 lines): `SQLiteManager` (:11) — `__init__` (:12-18), `_migrate_history_table` (:20-100), `_create_history_table` (:102), `_create_messages_table` (:128), `add_history` (:150), `batch_add_history` (:193), `get_history` (:227), `save_messages` (:257), `get_last_messages` (:298), `reset` (:326).
**Signature:** `add_history(record)` appends a history row; `get_history(memory_id)` returns the rows for a memory; `get_last_messages(session_scope, limit=10)` returns the last N messages; all under a `threading.Lock` (`check_same_thread=False`).
**Data Shape:** `history` table `{id, memory_id, old_memory, new_memory, event, created_at, updated_at, is_deleted, actor_id, role}`; `messages` table for session messages; `db_path` default `":memory:"`.

### Decisive source
```ts
class SQLiteManager:
    def __init__(self, db_path=":memory:"):
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self._lock = threading.Lock()
        self._migrate_history_table()   # rename old schema, create new, copy data, drop old
        self._create_history_table()
        self._create_messages_table()
    def _migrate_history_table(self):
        # if old group-chat columns, ALTER TABLE RENAME TO history_old,
        # CREATE TABLE history (new schema), copy intersecting data, DROP old
```

**Flow:** on init, migrate any legacy history table (rename → create new schema → copy intersecting data → drop old), then create the history + messages tables. All reads/writes under a `threading.Lock` (SQLite `check_same_thread=False` for cross-thread access). `add_history`/`batch_add_history` append; `get_history` reads per memory; `get_last_messages` returns the recent session messages.
**Invariant:** schema migration is idempotent (no duplicate migration on re-init); all access is thread-safe via the lock; history is append-only (event log of memory changes).
**Probe:** `tests/memory/` storage tests (migration from legacy schema; add/get history; batch add; get_last_messages; reset).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "SQLiteManager history migration add_history get_last_messages lock", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the SQLite history/messages storage with idempotent schema migration and thread-locked access; adapt the table schema and db path to host.
