<!-- capsule-v2 -->
# Segment manager file-handle LRU — How does the local manager stop thousands of persistent HNSW indexes from exhausting file descriptors?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** Every PersistentLocalHnswSegment holds open hnswlib file handles — what bounds them, and what must happen on eviction?

## LocalSegmentManager
**Path/Symbol:** `chromadb/segment/impl/manager/local.py:__init__` (:62-101), `hint_use_collection` (:222-238), `callback_cache_evict` (:103-112), `SEGMENT_TYPE_IMPLS` (:43-47), `_instance` (:245-251).
**Signature:** `_max_file_handles = resource.getrlimit(resource.RLIMIT_NOFILE)[0]` (Windows: `_getmaxstdio()`); `segment_limit = _max_file_handles // PersistentLocalHnswSegment.get_file_handle_count()`.
**Data Shape:** Two caches: per-scope segment caches (Basic or memory-bounded SegmentLRUCache keyed by COLLECTION id) + `_vector_instances_file_handle_cache: LRUCache[UUID, PersistentLocalHnswSegment]` whose callback closes handles.

### Decisive source
```python
if self._system.settings.require("is_persistent"):
    self._vector_segment_type = SegmentType.HNSW_LOCAL_PERSISTED
    ...
    segment_limit = (self._max_file_handles
        # This is integer division in Python 3, and not a comment.
        // PersistentLocalHnswSegment.get_file_handle_count())
    self._vector_instances_file_handle_cache = LRUCache(
        segment_limit, callback=lambda _, v: v.close_persistent_index())
...
def hint_use_collection(self, collection_id, hint_type):
    for type in [MetadataReader, VectorReader]:
        instance = self.get_segment(collection_id, type)
        if type == VectorReader and ...is_persistent:
            instance = cast(PersistentLocalHnswSegment, instance)
            instance.open_persistent_index()
            self._vector_instances_file_handle_cache.set(collection_id, instance)
```

**Flow:** writes/queries hint the manager → segments resolved through cache → sysdb-backed segment record → instance created under a lock (`with self._lock:` around `_instance`) and started once → persistent index handles opened and the instance re-pinned as MRU. Eviction closes hnswlib's mmapped files; the memory-side dicts survive so reopening is cheap. get_file_handle_count = hnswlib.Index.file_handle_count + 1 for the metadata pickle.
**Invariant:** Instance creation is globally serialized per manager; eviction MUST close OS handles before the slot is reused. The class docstring notes `get_file_handle_count`'s int-division footgun comment.
**Probe:** `/tmp/chroma-p1/probe_battery.py` mgr.* anchors incl rlimit source, division, evict-close callback, impl-map strings, lock-wrapped instantiation (GREEN).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "LocalSegmentManager LRUCache close_persistent_index hint_use_collection RLIMIT_NOFILE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt rlimit-derived handle budgets with close-on-evict for mmap-heavy engines; adapt to your fd accounting; omit Windows branch if unsupported.
