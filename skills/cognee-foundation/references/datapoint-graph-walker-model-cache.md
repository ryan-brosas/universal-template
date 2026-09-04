<!-- capsule-v2 -->
# DataPoint graph walker — model fields become nodes/edges, with a pydantic-leak fix

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How do you turn nested pydantic DataPoint objects (chunk.contains → Entity → EntityType …) into flat node/edge lists without infinite loops or leaking the LLM's memory?

## get_graph_from_model
**Path/Symbol:** `cognee/modules/graph/utils/get_graph_from_model.py:get_graph_from_model` (:178-322), `_simple_model_for` (:28-46), `_extract_field_data` (:49-92), `add_data_points` consumer `cognee/tasks/storage/add_data_points.py:79-95`.
**Signature:** `async get_graph_from_model(data_point, added_nodes=None, added_edges=None, visited_properties=None, include_root=True) -> (nodes: list[DataPoint], edges: list[(src_id, tgt_id, rel_name, props)])`.
**Data Shape:** Relationship fields are: a DataPoint, a list of them, `(Edge, DataPoint)`, or `(Edge, [DataPoint...])`; everything else is a node property. `belongs_to_set` special-cased to names for vector-side nodeset filtering.

### Decisive source
```python
# Memoized simple-node classes — WITHOUT this every call re-ran copy_model and
# minted a new BaseModel subclass; tracemalloc attributed +~50 MB per large-text
# cognify cycle to pydantic internals. Bounded LRU keyed by
# (DataPoint subclass, sorted excluded fields):
key = (data_point_type, tuple(sorted(excluded_fields)))
with _SIMPLE_MODEL_CACHE_LOCK:
    cached = _SIMPLE_MODEL_CACHE.get(key)
    if cached is not None:
        _SIMPLE_MODEL_CACHE.move_to_end(key); return cached
model = copy_model(data_point_type, exclude_fields=list(excluded_fields))
with _SIMPLE_MODEL_CACHE_LOCK:
    existing = _SIMPLE_MODEL_CACHE.get(key)      # re-check after heavy build —
    if existing is not None: return existing     # another thread may have raced us
    _SIMPLE_MODEL_CACHE[key] = model
    if len(_SIMPLE_MODEL_CACHE) > _SIMPLE_MODEL_CACHE_SIZE:  # 256, FIFO eviction
        _SIMPLE_MODEL_CACHE.popitem(last=False)
```

**Flow:** classify each field as property vs relationship → root node stored as a STRIPPED SimpleModel copy (relationship fields excluded so the graph node doesn't embed its whole subtree) → `_targets_generator` yields each (target, field_name, edge_meta); edge key `f"{src}_{tgt.id}_{field_name}"` guards duplicates; `visited_properties[f"{src}_{rel}_{tgt}"] = True` breaks cycles ("CRITICAL for preventing infinite loops"); recurse into unseen targets with shared added_nodes/added_edges dicts.
**Invariant:** (1) The class-memo cache is a MEMORY-LEAK fix, not an optimization garnish — unbounded subclass minting defeats itself if call-site exclusions vary (hence bounded). (2) Double-checked locking after copy_model is required because the build runs outside the lock. (3) add_data_points fans out per data point with SHARED added_nodes/added_edges/visited_properties dicts so one batch never writes a node twice.
**Probe:** coverage via `cognee/tests/unit/tasks/graph/test_extract_graph_from_data.py`; storage-level pins in `cognee/tests/unit/modules/storage/`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "_simple_model_for copy_model cache get_graph_from_model", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt field-classification walking + stripped root copies + shared dedup dicts + the bounded double-checked class cache; adapt edge property shape (`weight_*` expansion, updated_at string) to your graph store.
