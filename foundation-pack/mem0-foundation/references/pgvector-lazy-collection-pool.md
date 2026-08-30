<!-- capsule-v2 -->
# PGVector lazy collection + dual-psycopg pool — why does nothing touch the DB until first use, and how do psycopg2/3 share one code path?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** how does PGVector avoid blocking startup on an unreachable database while still guaranteeing the table exists before any operation?

## Connected graph-selected seam
**Path/Symbol:** `mem0/vector_stores/pgvector.py`: `PGVector.__init__` (:147-214, pool priority + `open=False`), `_ensure_collection` (:216-222), `_get_cursor` (:224-256).
**Signature:** `_ensure_collection(self)`; `_get_cursor(self, commit: bool = False)` contextmanager.
**Data Shape:** connection resolution priority `connection_pool` (caller-owned, used as-is) > `connection_string` (+sslmode merge) > individual params composed into a URI; module flag `PSYCOPG_VERSION` ∈ {2,3} selects pool/cursor behavior everywhere.

### Decisive source
```python
if PSYCOPG_VERSION == 3:
    # open=False avoids blocking when DB DNS is not yet resolvable (e.g. Docker startup)
    self.connection_pool = ConnectionPool(conninfo=connection_string,
        min_size=minconn, max_size=maxconn, open=False)
    self.connection_pool.open(wait=False)
...
def _ensure_collection(self):
    if self._collection_ensured:
        return
    collections = self.list_cols()
    if self.collection_name not in collections:
        self.create_col()
    self._collection_ensured = True
```

**Flow:** init only builds the (lazy) pool — no socket is opened (`open=False`, then non-blocking `open(wait=False)`) → every public method calls `_ensure_collection()` first: one `information_schema` list_cols round-trip, create if missing, then a once-per-instance latch short-circuits all later calls → all I/O funnels through `_get_cursor`, which yields a cursor, commits when `commit=True`, rolls back and re-raises on exception (psycopg3 delegates cleanup to pool context manager; psycopg2 manually closes cursor + `putconn` in finally).
**Invariant:** construction NEVER touches the network — a container whose DNS isn't up yet constructs fine and fails later at first real query; the ensured-latch means exactly one existence check per instance lifetime, so external DROP TABLE after first use is invisible to the latch (delete_col/create via reset() re-create eagerly); psycopg2's rollback happens BEFORE cursor close/pool return — reversing that order returns a poisoned connection to the pool.
**Probe:** `grep -c "_ensure_collection()" mem0/vector_stores/pgvector.py` (=9 guarded public entry points: insert/search/keyword_search/delete/update/get/col_info/list/reset); `grep -n "open(wait=False)" mem0/vector_stores/pgvector.py`.
**Direct test:** `tests/vector_stores/test_pgvector.py::test_init_does_not_block_on_unreachable_host_psycopg3` (:75) pins lazy construction; `test_transaction_rollback_on_error_psycopg2` (:1888) / `test_commit_on_success_psycopg2` (:1933) pin cursor-context semantics.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "_get_cursor unified context manager rollback commit pool PGVector", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lazy-open + first-use ensure + single funneling context manager as the porting shape for any SQL-backed vector store; adapt pool library specifics per driver version; omit none of the ordering (rollback before release, latch set only after successful check). Direct tests cover both arms (no caveat).
