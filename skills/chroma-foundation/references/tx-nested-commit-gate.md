<!-- capsule-v2 -->
# Tx nested commit gate — How do unrelated components share one SQLite connection without committing each other's half-done work?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** Segment components nest `with db.tx()` calls freely — what makes reentrant transactions safe?

## TxWrapper
**Path/Symbol:** `chromadb/db/impl/sqlite.py:TxWrapper.__enter__/__exit__` (:28-60), `SqliteDB.tx` (:140-144).
**Signature:** `__enter__ -> Cursor`; state is a `threading.local` stack `_tx_stack.stack`; connection borrowed from a pool (PerThreadPool when persistent, LockPool over `file::memory:?cache=shared` otherwise).
**Data Shape:** stack depth 0 ⇒ this context OPENS the transaction; depth >0 ⇒ joins the outer transaction.

### Decisive source
```python
def __enter__(self) -> base.Cursor:
    if len(self._tx_stack.stack) == 0:
        self._conn.execute("PRAGMA case_sensitive_like = ON")
        self._conn.execute("BEGIN;")
    self._tx_stack.stack.append(self)
    return self._conn.cursor()

def __exit__(self, exc_type, exc_value, traceback) -> Literal[False]:
    self._tx_stack.stack.pop()
    if len(self._tx_stack.stack) == 0:
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
    self._conn.cursor().close()
    self._pool.return_to_pool(self._conn)
    return False   # never suppress: exceptions propagate AFTER rollback
```

**Flow:** innermost callers get cursors on the same connection; only the OUTERMOST exit commits or rolls back; returning `False` guarantees the original exception still propagates after cleanup. PRAGMAs are set at BEGIN time per outermost transaction (`case_sensitive_like`) plus once at start() with `foreign_keys = ON`.
**Invariant:** All-or-nothing per call tree — a failure anywhere rolls back every nested component's writes; a nested block must NEVER commit early. The connection returns to the pool only after final commit/rollback.
**Probe:** `/tmp/chroma-p1/probe_battery.py` db.* checks (commit-gate anchor byte-exact, both case_sensitive_like sites counted — GREEN). Upstream: migration + queue tests exercise nesting implicitly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "TxWrapper tx_stack BEGIN commit rollback return_to_pool", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the depth-gated transaction wrapper for any shared-connection store; adapt pooling strategy to your runtime (per-thread vs lock); omit the in-memory shared-cache mode unless you need ephemeral DBs.
