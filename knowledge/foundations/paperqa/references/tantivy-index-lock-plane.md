<!-- capsule-v2 -->
# Tantivy SearchIndex lock-retry plane — how do concurrent indexers share one on-disk tantivy index safely?

**Source:** paper-qa (Apache-2.0) `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** Multiple async tasks (and separate processes) write one tantivy index — what retry/cache protocol prevents LockBusy crashes and duplicate Index opens?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/agents/search.py:_OPENED_INDEX_CACHE` (:96-110), `SearchIndex.add_document` (:275-329), `delete_document`/`save_index` (:331-379), `index` property (:185-209).
**Signature:** `async def add_document(self, index_doc: dict, document=None, lock_acquisition_max_retries=1000) -> None`.
**Data Shape:** `filecheck(filename, body_filehash)` gates every add (skip already-indexed); docs stored under `{md5(body)}.{ext}` in a docs/ dir; storage enum JSON_MODEL_DUMP | PICKLE_COMPRESSED | PICKLE_UNCOMPRESSED picks serialization + extension.

### Decisive source
```python
except ValueError as e:
    if "Failed to acquire Lockfile: LockBusy." in str(e):
        raise AsyncRetryError("Failed to acquire lock.") from e   # → tenacity retry
...
@retry(stop=stop_after_attempt(1000),
       wait=wait_random_exponential(multiplier=0.25, max=60),
       retry=retry_if_exception_type(AsyncRetryError))
async def delete_document(...)   # same ladder; reraise=True
```
Index-open cache (all-synchronous critical section):
```python
# All of the following operations are *synchronous* so we are not giving
# the opportunity for an await to switch to another parallel version of this code.
if key not in _OPENED_INDEX_CACHE:  Index.open(...)
else:                               reuse
_OPENED_INDEX_CACHE[key] = self._index, prev_count + 1   # refcount; __del__ decrements
```

**Flow:** add → filecheck → writer.add_document → record filehash → optional document blob write → caller batches commits (`process_file` counts `batched_save_counter == settings.agent.index.batch_size` then `save_index`). Failed parses mark `FAILED_DOCUMENT_ADD_ID="ERROR"` AND save immediately so crashed runs RESUME without re-parsing (:531-548).
**Invariant:** Commit batching means a crash loses at most `batch_size` files but never corrupts (tantivy commits atomic); the cache-refcount block must contain NO awaits; LockBusy detection is string-matching on ValueError because tantivy-py raises generic types.
**Probe:** `tests/test_agents.py` exercises directory indexing; executed grep pins `"Failed to acquire Lockfile: LockBusy."` at :318/:343/:373 and the no-await comment at :196-199.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "_OPENED_INDEX_CACHE AsyncRetryError LockBusy", limit: 10 });
```

## Verdict
Adopt refcounted open-cache + string-matched LockBusy retry ladder for any tantivy/lmdb-style single-writer store; adapt retry budget to your workload; omit progress-bar plumbing. Probe caveat: concurrency behavior verified by source reading + mechanical greps, not a live race test.
