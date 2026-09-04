<!-- capsule-v2 -->
# Reset & teardown ladder — how do you tear down a multi-backend memory instance without orphaned clients or zombie singletons?

**Source:** mem0 MIT `main@001c2352`; Codebase Memory `mem0`. **Question:** what is the reset/close choreography across SQLite, vector store, entity store, and telemetry?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/main.py`: `Memory.reset` (:2124-2154), `Memory.close` (:2156-2160), async twins (:3816, :3849); telemetry shutdown `_shutdown_oss_telemetry` (telemetry.py :177-183) via atexit.
**Signature:** `reset()` — wipe all data, keep the instance usable; `close()` — release resources, instance dead.
**Data Shape:** entity store participates ONLY if lazily initialized (`self._entity_store is not None`).

### Decisive source
```python
self.db.reset()
self.db.close()
self.db = SQLiteManager(self.config.history_db_path)   # fresh history DB

if hasattr(self.vector_store, "reset"):
    self.vector_store = VectorStoreFactory.reset(self.vector_store)
else:
    logger.warning("Vector store does not support reset. Skipping.")
    self.vector_store.delete_col()                     # fallback: drop + recreate
    self.vector_store = VectorStoreFactory.create(...)
# Reset entity store if initialized
if self._entity_store is not None:
    try:
        self._entity_store.reset()
    except Exception as e:
        logger.warning(f"Failed to reset entity store: {e}")
    self._entity_store = None                          # back to lazy-uninitialized
```

**Flow:** reset = db.drop-and-recreate → vector store capability-probe (`hasattr reset`) with delete-col+recreate fallback → best-effort entity-store reset then demote to None so the next touch rebuilds it; close = only the SQLite handle (vector stores own their connections). Telemetry's process-wide singleton shuts down once at interpreter exit through an atexit handler guarded by the same lock.
**Invariant:** reset preserves the INSTANCE (post-reset adds work normally) while close does not; the lazy entity store must be nulled after reset or stale collection handles survive the wipe; capability detection (hasattr) keeps stores that lack reset() working — no registry of "supports reset" to drift.
**Probe:** `tests/memory/test_storage.py::test_reset_drops_tables` (:284); `tests/vector_stores/test_qdrant.py::test_reset_clears_points_on_local_qdrant` (:57); telemetry singleton shutdown pinned in `tests/test_telemetry.py::test_shutdown_clears_singleton` (:254).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "reset delete_col entity_store _entity_store None close telemetry atexit", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt capability-probed reset + lazy-store demotion-to-None + one-shot atexit telemetry shutdown; adapt per-backend reset implementations.
