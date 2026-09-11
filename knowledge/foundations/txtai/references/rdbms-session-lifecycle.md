<!-- capsule-v2 -->
# RDBMS session lifecycle — when does a content database connect, and what dies with the connection?

**Source:** txtai Apache-2.0 `master@a10667a1c2a4721ce719f3648bd1aeedd03dd84a` (9.13.0); Codebase Memory `txtai`. **Question:** When must a content store open its connection, what state is per-session rather than per-index, and who owns thread safety?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/database/rdbms.py:RDBMS.initialize` (:245-258), `.session` (:260-278), `.save` (:111-113), `.close` (:115-118); dialect: `sqlite.py:SQLite.connect` (:16-24).
**Signature:** `session(path=None, connection=None)`; `initialize()` → session + createtables + createindexes.
**Data Shape:** instance state = `self.connection`, `self.cursor`; per-session artifacts = registered custom functions, TEMP tables `batch` and `scores`.

### Decisive source
```python
def initialize(self):
    if not self.connection:
        # Create database session. Thread locking must be handled externally.
        self.session()
        self.createtables()
        self.createindexes()

def session(self, path=None, connection=None):
    self.connection = connection if connection else self.connect(path) if path else self.connect()
    self.cursor = self.getcursor()
    # Register custom functions - session scope
    self.addfunctions()
    # Create temporary tables - session scope
    self.createbatch()
    self.createscores()
```

**Flow:** insert/delete/query call `initialize()` (or guard on `if self.connection:`) → first use opens ONE connection + cursor for the instance's whole life → custom functions re-registered per session → `batch`/`scores` temp tables recreated per session (`CREATE TEMP TABLE IF NOT EXISTS`) → `load(path)` = `session(path)` only ("thread locking must be handled externally"); `save(path)` after load is just `self.connection.commit()`.

**Flow (embedded save):** `Embedded.save` (:33-55) three-way branch — no prior path: commit → `copy(path)` → close temp → `session(connection=new)` + record path; same path: commit only; different path: copy and KEEP current connection.

**Invariant:** The batch/scores temp tables are SESSION-SCOPE — any port that persists them to disk or skips recreating them on reconnect breaks every subsequent similar()/delete query. There is exactly one connection per instance and no pooling: concurrent callers need an external lock (the Embeddings layer serializes). WAL is opt-in via `{"sqlite": {"wal": True}}` read through `setting()`.

**Probe:** `test/python/testdatabase/testrdbms.py` `Common.TestRDBMS.testSave` (:618-639 save→load→upsert offsets still work), `testSettings` (:641-655 wal pragma accepted).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "txtai", query: "RDBMS session initialize createbatch createscores connection", limit: 10, fields: ["signature", "name", "file"] });
```
Executed live at pin: top hits `RDBMS.session` (:260-278) and `RDBMS.insert` (:37-66), line-exact.

## Verdict
Adopt lazy single-connection lifecycle + session-scope temp tables/functions + commit-only save; adapt WAL/pragma toggles to your backend; omit the Client URL transport if embedded-only. Coverage: all cited paths no_recorded_issue @ gen 2026-08-25T20:20:01Z.
