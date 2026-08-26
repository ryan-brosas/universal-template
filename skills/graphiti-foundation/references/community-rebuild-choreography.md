<!-- capsule-v2 -->
# Community rebuild choreography — scoped wipe, odd-one-out tree, mode-community attach

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** how do communities get rebuilt without orphaning members, and how does a NEW entity join one mid-stream without a full rebuild?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/utils/maintenance/community_operations.py`: `remove_communities` (:244-271, `if group_ids:` :256), `build_communities` (:216-241, `MAX_COMMUNITY_BUILD_CONCURRENCY = 10` :20), `build_community` pairwise reduction (:174-213, `odd_one_out` ×4), `determine_entity_community` (:274-337), `update_community` (:340-367); orchestrator entrypoints `graphiti_core/graphiti.py:build_communities` (:1490-1526) + per-node hook (:1187); interface surface `graph_operations.py:GraphOperationsInterface.get_communities_by_nodes` (:709-725).
**Signature:** `async build_communities(driver, llm_client, group_ids: list[str] | None) -> tuple[list[CommunityNode], list[CommunityEdge]]`; `async determine_entity_community(driver, entity) -> tuple[CommunityNode | None, bool]` (node, is_new).
**Data Shape:** CommunityNode carries `name` (LLM description), `summary`, `group_id` inherited from `community_cluster[0]`, `labels=['Community']`, `created_at=utc_now()`; HAS_MEMBER edges built by `build_community_edges(cluster, node, now)`.

### Decisive source
```python
# community_operations.py — the scoping asymmetry
if group_ids:
    await driver.execute_query("""
        MATCH (c:Community)
        WHERE c.group_id IN $group_ids
        DETACH DELETE c
    """, group_ids=group_ids)
else:
    await driver.execute_query("MATCH (c:Community) DETACH DELETE c")
# [] is "no scoping requested" → full delete. Direct test pins this:
# tests/utils/maintenance/test_remove_communities.py:60
# test_remove_communities_empty_group_ids_deletes_all  ("WHERE not in query")

# build_community :179-197 — odd-one-out reduction tree
while length > 1:
    odd_one_out: str | None = None
    if length % 2 == 1:
        odd_one_out = summaries.pop()      # carried to NEXT round untouched
        length -= 1
    new_summaries = list(await semaphore_gather(*[
        summarize_pair(llm_client, (str(l), str(r)))
        for l, r in zip(summaries[: int(length / 2)],
                        summaries[int(length / 2):], strict=False)
    ]))
    if odd_one_out is not None:
        new_summaries.append(odd_one_out)
```

**Flow (rebuild):** `graphiti.build_communities(group_ids)` FIRST calls `remove_communities(scoped)` — wipe and rebuild share the same scope so stale communities can't survive — then clusters (`get_community_clusters`) and reduces each cluster's summaries pairwise under `Semaphore(10)`; the final summary feeds `generate_summary_description` for the name; embeddings+nodes+edges save via semaphore_gather fan-out.
**Flow (incremental):** on every `add_episode(..., update_communities=True)` each resolved entity runs `update_community` → `determine_entity_community` returns existing membership (HAS_MEMBER backpointer, `is_new=False`) or the MODE community of RELATES_TO-neighbors' communities (`is_new=True`; max_count==0 → `(None, False)` → caller skips) → summarize_pair(entity.summary, community.summary) REPLACES the community summary/name in place; only genuinely-new members append an edge.
**Invariant:** (1) empty-list vs None are the SAME scope decision everywhere in this plane ([] = unscoped), unlike Falkor routing where [] means don't-route; (2) odd summaries ride forward rather than being force-paired — pairing a leftover with a fresh summary would double-count it; `zip(strict=False)` tolerates the even split; (3) incremental updates mutate ONE community's summary — they never re-cluster — so membership is sticky between rebuilds; (4) concurrency caps differ by stage: clustering fans out unbounded via semaphore_gather inside each group, but LLM summarization is capped at 10.
**Probe:** `cd /mnt/hdd/utopia/inspo/memory/graphiti && grep -c 'odd_one_out' graphiti_core/utils/maintenance/community_operations.py` → `4`; `grep -c 'MAX_COMMUNITY_BUILD_CONCURRENCY' graphiti_core/utils/maintenance/community_operations.py` → `2`; `grep -n 'if group_ids:' graphiti_core/utils/maintenance/community_operations.py` → `256:`; direct tests `tests/utils/maintenance/test_remove_communities.py` all five (`test_remove_communities_unscoped_deletes_all` :33 asserts `'WHERE' not in query`, `test_remove_communities_scoped_via_graph_ops` :88 pins the graph_ops fallback ordering).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "remove_communities build_community odd_one_out determine_entity_community", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt scoped-wipe-then-rebuild as the only safe community refresh (partial rebuilds leave orphans); adapt the pairwise tree to your summary budget; omit the incremental mode-community attach only if you rebuild on every write. The empty-vs-None scoping asymmetry against the routing plane is the trap a porter will not see coming.
