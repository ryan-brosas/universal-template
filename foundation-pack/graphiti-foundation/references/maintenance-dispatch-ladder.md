<!-- capsule-v2 -->
# Maintenance dispatch ladder — how do legacy free functions stay correct across four backends when some have a capability interface and others don't?

**Source:** Graphiti Apache-2.0 `main@401c59a` (`graphiti_core/utils/maintenance/graph_data_operations.py`); Codebase Memory `graphiti`. **Question:** What is the correct layering when a utility must use the new `graph_operations_interface` where available but keep working byte-for-byte for drivers that lack it?

## Capability-probe → NotImplementedError fallback → dialect-keyed SQL assembly
**Path/Symbol:** `graphiti_core/utils/maintenance/graph_data_operations.py:clear_data` (:34–64), `retrieve_episodes` (:67–167), `EPISODE_WINDOW_LEN = 3` (:29).
**Signature:** `async def clear_data(driver: GraphDriver, group_ids: list[str] | None = None)`; `async def retrieve_episodes(driver: GraphDriver, reference_time: datetime, last_n: int = EPISODE_WINDOW_LEN, group_ids: list[str] | None = None, source: EpisodeType | None = None, saga: str | None = None) -> list[EpisodicNode]`.
**Data Shape:** `retrieve_episodes` returns episodes ordered DESC from the DB then reversed in Python → chronological ascending to callers.

### Decisive source
```python
async def clear_data(driver: GraphDriver, group_ids: list[str] | None = None):
    if driver.graph_operations_interface:
        try:
            return await driver.graph_operations_interface.clear_data(driver, group_ids)
        except NotImplementedError:
            pass

    async with driver.session() as session:
        async def delete_group_ids(tx):
            labels = ['Entity', 'Episodic', 'Community']
            if driver.provider == GraphProvider.KUZU:
                labels.append('RelatesToNode_')
            for label in labels:
                await tx.run(
                    f"""
                    MATCH (n:{label})
                    WHERE n.group_id IN $group_ids
                    DETACH DELETE n
                    """,
                    group_ids=group_ids,
                )
        if group_ids is None:
            await session.execute_write(delete_all)
        else:
            await session.execute_write(delete_group_ids)
```
and the saga-scoped retrieval branch:
```python
if saga is not None:
    group_id = group_ids[0] if group_ids else None
    ...
    MATCH (s:Saga {name: $saga_name, group_id: $group_id})-[:HAS_EPISODE]->(e:Episodic)
    WHERE e.valid_at <= $reference_time
    ...
episodes = [get_episodic_node_from_record(record) for record in records]
return list(reversed(episodes))  # Return in chronological order
```

**Flow:** both helpers try `driver.graph_operations_interface.<fn>` FIRST, swallow ONLY `NotImplementedError` (partial implementations degrade cleanly), then fall through to the legacy session path. Legacy `clear_data` branches on group scope: `None` ⇒ `MATCH (n) DETACH DELETE n` (nuke-all), else label-enumerated scoped deletes with a Kuzu-specific `RelatesToNode_` label appended (the edge-as-node modeling from `kuzu-edge-as-node`). Legacy `retrieve_episodes` builds filters additively (group_ids IN / source equality), swaps the RETURN projection on `driver.provider == NEPTUNE` (comma-string embeddings need different column shaping), supports the saga join path taking `group_ids[0]` only, and enforces the window via `ORDER BY valid_at DESC LIMIT $n` + Python `reversed()`.
**Invariant:** callers get CHRONOLOGICAL order even though the query is DESC — the reversal happens after hydration, never in SQL; the NotImplementedError swallow is the only acceptable exception to eat (any other error propagates); saga mode intentionally narrows multi-group calls to the first group.
**Probe:** mock-level only — `tests/test_graphiti_mock.py` exercises `Graphiti.retrieve_episodes` (graphiti.py:978 delegates here); no direct suite pins `clear_data`/saga SQL text. Coverage caveat recorded; deterministic probe = assert reversed-order contract and NotImplementedError-only swallowing on a stub driver.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "clear_data retrieve_episodes EPISODE_WINDOW_LEN", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder shape: capability probe with typed-exception fallback keeps one API surface while drivers migrate at their own pace. Adapt the label sets and projection swap to your dialect matrix. Omit the Kuzu label append unless you also adopt edge-as-node modeling. This is the seam the pass-5 capsules assumed but never cited — `graph_data_operations.py` is now on the citation map.
