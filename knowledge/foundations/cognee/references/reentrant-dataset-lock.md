<!-- capsule-v2 -->
# Re-entrant dataset lock — ContextVar-held marker instead of reentrant locks

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How do you serialize pipeline runs per dataset while letting a nested run on the SAME dataset (cognify_session → add/cognify) proceed without self-deadlocking?

## dataset_lock + held_datasets
**Path/Symbol:** `cognee/infrastructure/locks/dataset_lock.py:dataset_lock` (:44-66), `held_datasets` (:28), `get_dataset_lock` (:33-40); consumer `cognee/modules/pipelines/operations/pipeline.py:run_pipeline_per_dataset` (:113-175) + `_drive_marking_held` (:38-58).
**Signature:** `@asynccontextmanager async def dataset_lock(dataset_id: UUID)`; `held_datasets: ContextVar[frozenset]` (default `frozenset()`).
**Data Shape:** `_dataset_locks: dict[UUID, asyncio.Lock]` created lazily under an asyncio guard lock. Process-local ONLY (documented: does NOT protect multiple workers — DB-backed lock is future work).

### Decisive source
```python
if dataset_id in held_datasets.get():
    yield                       # re-entrant: ancestor holds it, don't re-acquire
    return
async with await get_dataset_lock(dataset_id):
    token = held_datasets.set(held_datasets.get() | {dataset_id})
    try: yield
    finally: held_datasets.reset(token)
```
The pipeline layer marks held WHILE THE BODY ADVANCES, resetting before every yield:
```python
marked = held_datasets.get() | {dataset_id}
while True:
    token = held_datasets.set(marked)
    try: item = await source.__anext__()
    except StopAsyncIteration: return
    finally: held_datasets.reset(token)
    yield item
```

**Flow:** external run acquires the plain non-reentrant Lock and wraps its body in `_drive_marking_held`; the run's actual work happens in child tasks (`run_tasks` → `create_task`) which COPY the current context — so the held-marker propagates into them; a nested run on the same dataset sees the marker and takes the direct path.
**Invariant:** The reset-before-yield placement is load-bearing: holding the marker ACROSS a yield would leak it into the foreground driver and make a LATER unrelated background run wrongly skip the lock. ContextVar (not a global set) is what makes child-task inheritance work; plain `asyncio.Lock` stays non-reentrant because re-entrancy is handled one level up.
**Probe:** `cognee/tests/unit/infrastructure/locks/test_dataset_lock.py::test_reentrant_acquire_does_not_deadlock`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "held_datasets dataset_lock reentrant _drive_marking_held", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ContextVar held-set pattern for re-entrancy over any lock primitive; adapt the registry to cross-process if you have multi-worker needs cognee explicitly defers; omit the delete-operation sharing unless you port deletes too.
