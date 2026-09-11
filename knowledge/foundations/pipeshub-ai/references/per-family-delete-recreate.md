<!-- capsule-v2 -->
# Per-family delete-then-recreate — how does replacing an agent's toolsets/MCP/knowledge avoid both orphaned nodes and torn deletes?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** When a PUT replaces an entire attachment family (toolsets, MCP servers, knowledge) owned by the agent, in what order do you delete, and why is the delete committed BEFORE the re-create?

## Two-phase read-only gather → leaves-to-root delete, then a SEPARATE create transaction
**Path/Symbol:** `backend/python/app/api/routes/agent.py:update_agent` (:2425–2873); deletion phase :2432–2562 (toolsets), :2588–2718 (MCP), :2765–2854 (knowledge); creation helpers `_create_toolset_edges` / `_create_mcp_server_edges(transaction=...)` / `_create_knowledge_edges`.
**Signature:** `begin_transaction(read=[], write=[family collections])`; `get_edges_from_node(full_id, collection, transaction=)`; `delete_all_edges_for_node(full_id, collection, transaction=)->count`; `delete_nodes(keys, collection, transaction=)`.
**Data Shape:** Edge documents carry `_to = "collection/key"`; keys are split with the `SPLIT_PATH_EXPECTED_PARTS` guard (`parts = full_id.split("/", 1)`).

### Decisive source
```python
# ========== PHASE 1: GATHER ALL INFORMATION (READ ONLY) ==========
toolset_edges = await graph_provider.get_edges_from_node(agent_full_id,
    CollectionNames.AGENT_HAS_TOOLSET.value, transaction=transaction_id)
...
# ========== PHASE 2: DELETE FROM LEAVES TO ROOT ==========
# Step 1: Delete toolset -> tool edges ... must be done first before deleting tool nodes
for tool_full_id in all_tool_full_ids:
    count = await graph_provider.delete_all_edges_for_node(tool_full_id,
        CollectionNames.TOOLSET_HAS_TOOL.value, transaction=transaction_id)
# Step 2: Delete tool nodes (now safe, all their edges are gone)
await graph_provider.delete_nodes(all_tool_keys, CollectionNames.AGENT_TOOLS.value, transaction=transaction_id)
# Step 3: agent->toolset edges;  Step 4: toolset nodes
await graph_provider.commit_transaction(transaction_id)
transaction_id = None
...
# Create new nodes only if there are toolsets to create — its own transaction
created_toolsets, failed_toolsets = await _create_toolset_edges(
    agent_id, toolsets_with_tools, user_context, user_key,
    services["graph_provider"], logger)   # no transaction => helper manages its own txn scope
```

**Flow:** validate/parse new payload FIRST (a duplicate-typeId error aborts before any delete) → txn #1: gather all edges for the family inside the txn, delete leaf-edges → leaf-nodes → root-edges → root-nodes, commit → txn #2 (or untransacted helper): recreate from the validated payload. The MCP-server family even wraps its re-create in its OWN transaction (:2724–2761) so "failure partway rolls back rather than leaving orphaned MCP server/tool nodes with no AGENT_HAS_MCP_SERVER edge".
**Invariant:** (1) Deletion order is strictly edges-before-nodes, leaves-before-root; node deletes are safe only because every incident edge was removed first. (2) The delete of the OLD family and the create of the NEW one are separate transactions — never merged into one mega-txn. (3) Payload validation happens before the delete transaction starts, so a bad payload can't destroy existing attachments. (4) Skills are the counter-example: update NEVER deletes skill NODES, only this agent's `agentHasSkill` edges (:2875–2913) — skills are owned by the management API, not by referencing agents.
**Probe:** `integration-tests/response-validation/enterprise-search/agents/integration_test_agents.py` (`TestUpdateAgent._update_agent_raw` :1004–1024 round-trips updates); no unit test pins the ordering ladder — coverage caveat recorded; deterministic check = the four-step shape above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "delete_all_edges_for_node delete_nodes transaction", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-phase discipline (gather-reads inside the txn, leaves-to-root deletion, delete-committed-before-recreate, per-family transactions instead of one mega-transaction). Adapt the collection names and which families are "owned" vs "referenced" (owned ⇒ delete nodes+edges; referenced ⇒ unlink edges only). Omit the HTTP logging cosmetics.
