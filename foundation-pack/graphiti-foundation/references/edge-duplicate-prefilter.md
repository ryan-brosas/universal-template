<!-- capsule-v2 -->
# IS_DUPLICATE_OF pre-filter — provider-branched dedup of node-merge pairs

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** before writing duplicate-node merges, how do you skip pairs that already have the IS_DUPLICATE_OF edge — across graph backends with different relationship models?

## IS_DUPLICATE_OF pre-filter
**Path/Symbol:** `graphiti_core/utils/maintenance/edge_operations.py`: `filter_existing_duplicate_of_edges` (:850-911); Neptune branch (:860-878), Kuzu edge-as-node branch (:880-888), default Cypher branch (:889-903); map-pop subtraction (:905-911).
**Signature:** `async filter_existing_duplicate_of_edges(driver: GraphDriver, duplicates_node_tuples: list[tuple[EntityNode, EntityNode]]) -> list[tuple[EntityNode, EntityNode]]`.
**Data Shape:** input = ordered (source, target) node pairs proposed for merge; output = the subset with NO existing `RELATES_TO {name:'IS_DUPLICATE_OF'}` edge; Kuzu parameter rows are `{'src':..., 'dst':...}` while Neptune/default bind tuple-shaped rows.

### Decisive source
```python
# Three grammars, ONE predicate — Kuzu materializes relationships as nodes
# (see kuzu-edge-as-node capsule), so the match traverses TWO hops:
if driver.provider == GraphProvider.KUZU:
    query = """
        UNWIND $duplicate_node_uuids AS duplicate
        MATCH (n:Entity {uuid: duplicate.src})-[:RELATES_TO]->(e:RelatesToNode_ {name: 'IS_DUPLICATE_OF'})-[:RELATES_TO]->(m:Entity {uuid: duplicate.dst})
        RETURN DISTINCT n.uuid AS source_uuid, m.uuid AS target_uuid
    """
    duplicate_node_uuids = [{'src': src, 'dst': dst} for src, dst in duplicate_nodes_map]
else:
    # Neo4j/FalkorDB bind a LIST OF TUPLES directly; Neptune binds row dicts:
    MATCH (n:Entity {uuid: duplicate_tuple[0]})-[r:RELATES_TO {name: 'IS_DUPLICATE_OF'}]->(m:Entity {uuid: duplicate_tuple[1]})
...
# Subtract found pairs from the proposal map -> only genuinely-new merges survive:
for record in records:
    duplicate_tuple = (record.get('source_uuid'), record.get('target_uuid'))
    if duplicate_nodes_map.get(duplicate_tuple):
        duplicate_nodes_map.pop(duplicate_tuple)
return list(duplicate_nodes_map.values())
```

**Flow:** build `(source.uuid, target.uuid)` → pair map → early-return on empty input → branch query grammar by `driver.provider` (NEPTUNE ⇒ dict rows + `duplicate_node_uuids=duplicate_nodes`; KUZU ⇒ two-hop through `RelatesToNode_` with src/dst dicts; else ⇒ tuple-keyed single-hop) → execute read-only (`routing_='r'`) → pop every returned pair from the map → return survivors.
**Invariant:** (1) the filter is set-subtraction by exact uuid PAIR, order-sensitive — (A,B) and (B,A) are different keys, matching how upstream writes the directed edge; (2) Kuzu's `RelatesToNode_` intermediate is mandatory there — a single-hop pattern silently matches nothing on Kuzu; (3) all branches use DISTINCT so duplicate proposals don't multiply results.
**Probe:** anchored at repo root. Battery: `grep -c "MATCH (n:Entity {uuid: duplicate_tuple\[0\]})" graphiti_core/utils/maintenance/edge_operations.py` → 1; `grep -c 'RelatesToNode_ {name' graphiti_core/utils/maintenance/edge_operations.py` → 1; `grep -c "duplicate_nodes_map.pop" graphiti_core/utils/maintenance/edge_operations.py` → 1. Direct-test coverage caveat: no dedicated unit test pins this helper at pin `993e081a` (DB-backed suites parametrize to zero drivers in default CI — see tests/helpers_test.py:33-58 env-gated driver matrix); contract verified against source + callers.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "filter_existing_duplicate_of_edges IS_DUPLICATE_OF RELATES_TO", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the subtract-before-write idiom and the per-provider grammar split; adapt parameter shapes to your driver's binding rules; omit branches for backends you don't run. Coverage caveat stated above (no default-CI test).
