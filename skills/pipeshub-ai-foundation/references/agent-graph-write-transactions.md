<!-- capsule-v2 -->
# Agent graph-write transactions — how does a multi-entity CRUD route keep the property graph all-or-nothing?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** When one request must write nodes and edges across a dozen graph collections (agent + permissions + toolsets + tools + MCP + knowledge + skills), what runs inside the transaction, what is deliberately kept out, and how do partial attachment failures surface without corrupting the graph?

## One txn over all collections; validate-before-begin; rollback-guard by None-stamp; failures→warnings
**Path/Symbol:** `backend/python/app/api/routes/agent.py:create_agent` (:1676-2053, txn ladder :1748-2020); provider contract `app/services/graph_db/interface/graph_db_provider.py:begin_transaction(read, write)->str` / `commit_transaction(str)` / `rollback_transaction(str)` (ArangoDB impl is a thin HTTP passthrough over stream transactions, `arango_http_provider.py:801-829`). Same ladder re-per-route in `update_agent` (:2313+, per-section txns e.g. skill reassignment) and `delete_agent`.
**Signature:** `await graph_provider.begin_transaction(read=[AGENT_SKILLS], write=[AGENT_INSTANCES, PERMISSION, AGENT_TOOLSETS, AGENT_TOOLS, AGENT_HAS_TOOLSET, TOOLSET_HAS_TOOL, AGENT_MCP_SERVERS, AGENT_HAS_MCP_SERVER, MCP_SERVER_HAS_TOOL, AGENT_KNOWLEDGE, AGENT_HAS_KNOWLEDGE, AGENT_HAS_SKILL]) -> transaction_id`; every subsequent op passes `transaction=transaction_id`; `commit_transaction(tid)` / `rollback_transaction(tid)`.
**Data Shape:** Steps: agent node batch-upsert → OWNER permission edge (+optional org READER edge only when `shareWithOrg`) → toolset/tool node+edge fan-out → MCP servers → knowledge nodes (filters JSON-stringified) → skill LINKS (`_create_skill_edges`: edges to pre-existing `agentSkills` docs only — never creates a skill node). Response aggregates `created_*` plus `failed_toolsets/failed_mcp_servers` → `status: "success" | "partial_success"` with a warnings array.

### Decisive source
```python
transaction_id = await graph_provider.begin_transaction(...)
...  # steps 1-5: batch_upsert_nodes / batch_create_edges all carry transaction=tid
await graph_provider.commit_transaction(transaction_id)
transaction_id = None                      # THE guard: commit succeeded
...
except Exception as e:
    if transaction_id:                     # non-None => possibly-open txn => roll back
        try:
            await graph_provider.rollback_transaction(transaction_id)
        except Exception as abort_error:
            logger.error(f"Failed to abort transaction: {abort_error}")  # never masks e
    raise HTTPException(status_code=500, ...) from e
```

**Flow:** parse + cross-field validation BEFORE `begin_transaction` (models need ≥1 reasoning model; service-account forces `shareWithOrg=True`; toolsets/MCP/knowledge/skills parsed outside the txn) → begin with the full read/write collection manifest → execute steps 1-5 inside ONE transaction → commit then IMMEDIATELY stamp `transaction_id = None` → any exception rolls back only if the id is still set, converts to HTTP 500. Attachment resolution that fails INSIDE `_create_mcp_server_edges` etc. is recorded into `failed_*` lists instead of raising — the agent exists atomically while broken attachments surface as `partial_success` warnings.
**Invariant:** (1) ALL-or-nothing across every collection touched — no partial agent graphs after a failure. (2) The `None`-stamp between commit and except-block is the idempotence latch against rolling back a committed transaction; rollback failure is logged, never substituted for the original error. (3) No client-controllable validation work happens inside the transaction. (4) Skills are edge-only links to externally-owned documents — an agent route must never create/delete another subsystem's nodes (update_agent's skill section likewise deletes only this agent's `AGENT_HAS_SKILL` edges). (5) update_agent runs SEPARATE small transactions per section rather than one giant one — section isolation beats a single wide txn on the update path.
**Probe:** `backend/python/tests/unit/api/routes/test_agent_full_coverage.py::test_generic_exception_rollback` (:1097-1124 — mocked provider asserts `rollback_transaction.assert_called_once()` on generic exception; commit path asserted at :1074-1076); integration round-trips live in `integration-tests/response-validation/enterprise-search/agents/integration_test_agents.py` (create/delete/update).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "begin_transaction commit_transaction rollback_transaction create_agent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt validate-before-begin, one-txn-per-create with an explicit read/write collection manifest, the commit-then-None-stamp rollback guard, log-don't-mask rollback failures, and attachment-failures-become-warnings partial_success; adapt collection names and lock semantics (Arango stream transactions vs host DB) to host. Direct-test coverage is partial: rollback/commit paths mocked-provider tested; no test pins the full happy-path fan-out on real Arango. Companion capsules: `tombstone-delete-rollback-latch` (delete-path double-arm variant), `per-family-delete-recreate` (update-path two-phase ordering), `referenced-skill-link-gating` (edge-only skill linking).
