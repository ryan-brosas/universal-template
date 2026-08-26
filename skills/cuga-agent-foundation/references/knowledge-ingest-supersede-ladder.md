<!-- capsule-v2 -->
# Ingest supersede ladder — how do you stop a config change mid-ingest from writing old-embedder vectors under a NEW collection config?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How does a long-running ingest worker detect that the engine's embedding/chunking config changed underneath it, and what must it do at each stage?

## Generation capture + recheck ladder (outside lock AND inside lock)
**Path/Symbol:** `src/cuga/backend/knowledge/engine.py:2442-2447` (`worker_apply_gen = self._apply_generation` + `_check_supersede` closure), rechecks at `:2465`, `:2472`, `:2607`, and `:2623-2630` (inside the collection lock); bump site `commit_knowledge_update` `engine.py:3929-3933`; error type `ReindexSupersededError` `:789-800`.
**Signature:** `_check_supersede() -> None` raises `ReindexSupersededError(worker_gen, current_gen)` when `self._apply_generation != worker_apply_gen`; `_ingest_inner(collection, file_path, filename, task_id, replace_duplicates, cancel_event, skip_file_copy=False)`.
**Data Shape:** `_apply_generation: int` starts 0 (`engine.py:1800`); bumped ONLY by `commit_knowledge_update` and only when `embedding_changed or chunking_changed or metric_changed`. Worker captures its gen BEFORE any await; every subsequent check compares captured vs live int.

### Decisive source
```python
# engine.py:2619-2630 — why the LAST recheck must be INSIDE the lock
async with self._get_collection_lock(collection):
    # Re-check supersede INSIDE the lock, immediately before the
    # collection config is pinned + vectors inserted. The check at
    # 2477 is outside the lock, so a concurrent commit_knowledge_update
    # could bump _apply_generation between there and here; without
    # this a stale worker would pin _ensure_collection_config to the
    # NEW provider/dim and write old-embedder vectors under it — a
    # name-vs-content mismatch within the target collection.
    _check_supersede()
    await self._ensure_collection_config(collection)
```
The four checkpoints bracket the expensive stages: pre-parse (`:2465`), post-parse before metadata normalization (`:2472`), post-normalize pre-lock (`:2607`), and in-lock immediately before pinning collection config (`:2625`). A porter who checks only once — anywhere — leaves exactly the race the in-lock check closes: parse takes seconds-to-minutes (Docling), plenty of time for a PATCH+publish to swap provider/dim.

**Flow:** worker captures gen → parse → recheck → chrome-drop/normalize → recheck → acquire per-collection lock → RE-CHECK IN LOCK → pin config → insert → completion status. Superseded path: `except ReindexSupersededError` writes SQL status `"cancelled"` (the CHECK constraint admits no new value) and records the audit trail in `file_tasks[filename].status="superseded"` with reason `"config changed mid-ingest (gen N -> M)"` (`:2740-2758`).
**Invariant:** A stale worker must NEVER touch the target collection's config or vectors; the only authoritative check is the one executed while holding the same lock that serializes config pinning + insert. Generation bumps are monotonic ints owned solely by `commit_knowledge_update`.

**Probe:** `tests/unit/test_knowledge_apply_generation.py:27-55` (`test_stale_ingest_worker_records_superseded_when_apply_generation_bumps`) — `fake_load` bumps `_apply_generation` mid-flight; asserts final task `status=="cancelled"`, file status `"superseded"`, reason contains `"gen 0 -> 1"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebaseMemory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_ingest_inner _check_supersede ReindexSupersededError _apply_generation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the capture-once/recheck-per-stage pattern with the mandatory in-lock final recheck, and the split status (SQL `cancelled` + audit `superseded`). Adapt checkpoint placement to your own stage boundaries. Omit the Docling-specific stages freely — the ladder shape is the portable part.
