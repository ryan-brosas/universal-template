<!-- capsule-v2 -->
# Record parser split — dialect JSON pre-normalization vs shared typed hydration

**Source:** graphiti MIT `main@401c59a6`; Codebase Memory `graphiti`. **Question:** when one database returns a JSON column as a string and another returns it as an object, where should the divergence be absorbed so the typed-model hydration code stays single-sourced?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/driver/kuzu/operations/record_parsers.py:parse_kuzu_entity_node` (:25–34) / `parse_kuzu_entity_edge` (:37–46); shared base `graphiti_core/driver/record_parsers.py:entity_node_from_record` (:24–50), `entity_edge_from_record` (:53–85), `episodic_node_from_record` (:88–108).
**Signature:** `parse_kuzu_entity_node(record: Any) -> EntityNode` — mutates `record['attributes']` in place, then delegates; `entity_node_from_record(record: Any) -> EntityNode`.
**Data Shape:** input is a driver record (dict-like); `attributes` may arrive as str / dict / None depending on backend. Output is a Pydantic model (`EntityNode`, `EntityEdge`, `EpisodicNode`, `CommunityNode`).

### Decisive source
```python
# kuzu/operations/record_parsers.py — the ENTIRE dialect layer:
def parse_kuzu_entity_edge(record):
    if isinstance(record.get('attributes'), str):
        try:
            record['attributes'] = json.loads(record['attributes'])
        except (json.JSONDecodeError, TypeError):
            record['attributes'] = {}          # corrupt JSON degrades to {}, never raises
    elif record.get('attributes') is None:
        record['attributes'] = {}
    return entity_edge_from_record(record)

# driver/record_parsers.py — shared hydration assumes attributes is ALREADY a dict
def entity_node_from_record(record):
    attributes = record['attributes']
    for key in ('uuid', 'name', 'group_id', 'name_embedding',
                'summary', 'created_at', 'labels'):
        attributes.pop(key, None)   # reserved columns are stripped from the free map
```

**Flow:** Kuzu returns `attributes` as a serialized string → dialect parser deserializes-or-blanks → shared parser pops every reserved column key from the attribute map → builds the Pydantic model with top-level fields from named record columns. FalkorDB/Neo4j/Neptune call the shared parsers directly because their drivers return real maps.
**Invariant:** (1) corrupt JSON becomes `{}`, not an exception — a bad row must not kill a bulk read; (2) the reserved-key pop list IS the schema boundary: anything stored as a column must also be popped from attributes, or the model ends up with duplicated stale values inside `attributes`; (3) dates go through `parse_db_date` (None-tolerant) except episodic `created_at`/`valid_at`, which raise ValueError if unparseable — episodic nodes have no meaningful existence without their clocks.
**Probe:** no unit test imports these parsers directly (coverage caveat — behavior verified by whole-file read); integration pins live in `tests/test_node_int.py`/`test_edge_int.py` via round-trips.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "entity_node_from_record parse_kuzu_entity_node record parser", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-layer split (per-dialect pre-normalization → shared typed hydration) and the corrupt-JSON-to-empty-map rule; adapt the reserved-key list to your own column set; omit Kuzu entirely if you don't target it but keep the seam position identical.
