<!-- capsule-v2 -->
# Neptune vector/list encoding traps — comma joins, key removals, and a latent entity_edges bug

**Source:** graphiti MIT `main@401c59a6`; Codebase Memory `graphiti`. **Question:** when a property store can't hold arrays or vectors natively, which encodings does each save query apply on the way IN — and which decode must pair with them on the way OUT?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/models/nodes/node_db_queries.py:get_episode_node_save_query` NEPTUNE branch (:33–38) vs `EPISODIC_NODE_RETURN_NEPTUNE` (:124–134); `get_entity_node_save_query` NEPTUNE branch (:164–174); `graphiti_core/models/edges/edge_db_queries.py:get_entity_edge_save_query` NEPTUNE branch (:74–83), `EPISODIC_EDGE_RETURN`/`COMMUNITY_EDGE_RETURN` (:54–60, :299–305).
**Signature:** save queries are `(provider, ...) -> str` Cypher templates; return fragments are per-provider SQL SELECT lists aliased into the shared record shape.
**Data Shape:** Neptune openCypher has no native array/vector property type: embeddings become CSV strings via `join([x IN coalesce($v, []) | toString(x)], ",")`; lists become joined strings; the Python-side parameter map keeps the original types.

### Decisive source
```python
# node_db_queries.py :36 — episode save JOINS with '|'
"entity_edges: join([x IN coalesce($entity_edges, []) | toString(x)], '|'), ..."
# node_db_queries.py :133 — Neptune episode return SPLITS ON ','
split(e.entity_edges, ",") AS entity_edges     # <-- latent BUG: never yields >1 element

# Correct pairing exists for edge episodes (:81 join ',' ↔ :224 split ','):
SET e.episodes = join($edge_data.episodes, ",")
split(e.episodes, ',') AS episodes

# And embeddings are REMOVED from the flat map before re-setting as strings:
SET e = removeKeyFromMap(removeKeyFromMap($edge_data, "fact_embedding"), "episodes")
SET e.fact_embedding = join([x IN coalesce($edge_data.fact_embedding, []) | toString(x)], ",")
```

**Flow:** save = strip non-native-typed keys from the bulk map → set them individually as encoded strings → read = split/join back to typed values with matching delimiter.
**Invariant:** (1) every comma-joined encoding MUST be paired with a comma-split on read — `episodes` proves the intended pattern; (2) the flat `SET e = $map` must exclude keys you re-set individually, or the string encoding gets overwritten by the raw value (hence `removeKeyFromMap(removeKeyFromMap(...))`); (3) **known latent defect**: episodic-node save uses `'|'` join for `entity_edges` while the Neptune return fragment splits on `','` — multi-edge episodes silently truncate to their first element on Neptune reads; pinned by NO test (`tests/test_edge_db_queries.py:31` only checks the episodes split). A porter must copy the pairing discipline, not either half alone.
**Probe:** `tests/test_edge_db_queries.py:31 test_neptune_uses_start_end_node_with_split_episodes` (pins `split(e.episodes, ',')`); `:57 test_entity_edge_return_query_selects_reference_time` (pins temporal aliasing across all providers).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "NEPTUNE removeKeyFromMap join toString entity_edges episodes", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the encode-on-write/pair-decode-on-read discipline and the removeKeyFromMap ordering; adapt delimiters freely BUT keep both halves in one module so the pairing is greppable; treat the `'|'`-join/`','`-split mismatch as a bug to fix, not behavior to copy.
